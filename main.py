import io

import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from urllib.parse import urljoin
from my_proxy_smtplib import ProxySMTP
from threading import Thread

import os
import sys
import getopt
import traceback

import json
from collections import defaultdict

import time
from time import strftime
import random

import re

import uritool
import myers
import utils
import notiontool
import parsertool


config = None
mailsession = None
defaultEncoding = 'utf-8'


def buildMailBody(subject, content, link=None, sendAsHtml=True, encoding=None):
    global defaultEncoding

    if encoding is None:
        encoding = defaultEncoding

    if sendAsHtml:
        baseurl = None
        if link is not None:
            # content = '<p><a href="' + link + '">' + subject + '</a></p>\n' + content
            baseurl = urljoin(link, '/')
        mail = MIMEText('<html><head><title>' + subject + '</title>' + ('<base href="' + baseurl + '">' if baseurl else '') + '</head><body>' + content + '</body></html>', 'html', encoding)
    else:
        if link is not None:
            content = link + '\n\n' + content
        mail = MIMEText(content, 'plain', encoding)

    mail['Subject'] = Header(subject, encoding)
    return mail


def sitesToMailSubject(sites):
    # Input: User's changed sites list
    # Output: If multiple sites then "[name1] and x more sites have updated!". 
    # If one site then "[name1] has updated!"
    name = sites[0]["name"]
    others_count = len(sites) - 1
    if others_count == 0:
        subject = "[{}] has updated!".format(name)
    elif others_count == 1:
        subject = "[{}] and {} more site have updated!".format(name, others_count)
    else:
        subject = "[{}] and {} more sites have updated!".format(name, others_count)
    return subject


def sitesToMail(subject, sites, sendAsHtml=True, encoding=None):
    # Return mail object for sites. Use this to generate mail that to inform user sites updates. 
    # TODO: Use templates to render html mail independently as web page. 
    global defaultEncoding
    
    if encoding is None:
        encoding = defaultEncoding

    mail_content = ''

    if sendAsHtml:
        for site in sites:
            content = '<p><a href="' + site['uri'] + '">' + site['name'] + '</a></p>\n' + site['changes'] + '\n\n<hr>'
            mail_content += content
        mail_content = re.sub('\<hr>$', '', mail_content)
        mail = buildMailBody(subject, mail_content, None, sendAsHtml, encoding)
    else:
        for site in sites:
            content = site['uri'] + '\n' + site['changes'] + '\n\n'
            mail_content += content
        mail = buildMailBody(subject, mail_content, None, sendAsHtml, encoding)

    return mail


def sendmail(receivers, mail, sendAsHtml, encoding=None):
    global mailsession

    if encoding is None:
        encoding = defaultEncoding

    mail['From'] = formataddr((str(Header(config["senderName"], encoding)), config["sender"]))
    mail['To'] = ", ".join(receivers)

    # initialize session once, not each time this method gets called
    if mailsession is None:
        if config["useSmtpProxy"] is True:
            mailsession = ProxySMTP(config["smtphost"], config["smtpport"], proxy_addr='127.0.0.1', proxy_port=7890)
        else:
            mailsession = smtplib.SMTP(config["smtphost"], config["smtpport"])

        if config["useTLS"]:
            mailsession.ehlo()
            mailsession.starttls()
        if config["smtpusername"] is not None:
            mailsession.login(config["smtpusername"], config["smtppwd"])

    mailsession.send_message(mail)


def storeSite(site):
    # Store site data in site['name'].txt file.
    # Whole site dictionary will be saved. 
    if 'changes' in site:
        site = site.copy()
        site.pop('changes')

    file_path = os.path.join(config["workingDirectory"], site["name"] + '.txt')
    with open(file_path, 'w') as thefile:
        thefile.write(json.dumps(site))


def getStoredSite(site_name):
    stored_str = ''

    file_path = os.path.join(config["workingDirectory"], site_name + '.txt')
    if os.path.exists(file_path):
        with open(file_path, 'r') as thefile:
            for line in thefile:
                stored_str += line
        return json.loads(stored_str)
    else:
        return defaultdict(str)


def pollWebsites(sites):
    """Poll all monitored sites, save updated ones and send notify mail to subscribers. 

    Fetch all monitored sites from config then parse them. If there is difference between saved content then save 
    the new content and send update mail to subscribed users. Mail body is the inserted lines using myers algorithm.

    Args:
        sites: A list from config, config['sites']. Including dictionaries of each site. 

    Todo:
        Send mail by message queue. 
        Use MongoDB to save the sites. 
    """
    global defaultEncoding

    send_dict = {}

    for i, site in enumerate(sites):
        site_name = site['name']
        print('polling site [' + site_name + '] ...')

        try:
            raw_contents = uritool.URLReceiver(uri=site['uri'], contenttype=site['contentType'], userAgent=config['userAgent']).performAction()
            if site['parserType'] and site['path']:
                parser = parsertool.ParserGenerator.getInstance(site['parserType'], site['path'])
                raw_contents = parser.performAction(raw_contents)
        except Exception as e:
            subject = "[Error] " + str(e.code) + " happened when polling " + site_name
            content = str(e.code) + ' ' + e.reason
            mail = buildMailBody(subject, content, link=site['uri'], sendAsHtml=False)
            sendmail([config['administrator']], mail, False)
            continue

        site_previous = getStoredSite(site_name)

        # raw_contents will only have one element in the list. 
        for content in raw_contents:
            # Only send update mail when site file exists and updated. 
            if not site_previous:
                site['content'] = content.content
                storeSite(site)
            elif content.content != site_previous['content']:
                site['content'] = content.content

                storeSite(site)

                changes = myers.get_inserts(site_previous['content'].splitlines(), content.content.splitlines())
                changes = '\n'.join(changes)
                site['changes'] = changes

                # sender_dict: A dictionary like {subscriber:[idx1, idx2, ...]}. 
                # The idxs are site index in sites list that the user subscribed and got updated. 
                for subscriber in site['subscribers']:
                    if subscriber in send_dict:
                        send_dict[subscriber].append(i)
                    else:
                        send_dict[subscriber] = [i]
    
    for subscriber, sites_idxs in send_dict.items():
        changed_subscribed_sites = [sites[i] for i in sites_idxs]

        subject = sitesToMailSubject(changed_subscribed_sites)

        mail = sitesToMail(subject, changed_subscribed_sites)

        # sendmail([subscriber], mail, True)
        send_mail_thr = Thread(target = sendmail, args = [[subscriber], mail, True])
        send_mail_thr.start()


def _main():
    global config

    notiontool.pull_config()
    config = utils.loadConfig()
    sites = config['sites']

    pollWebsites(sites)
    print('Polling Finished!')


if __name__ == '__main__':
    _main()
