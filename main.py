import io
import hashlib

import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from urllib.parse import urljoin
from my_proxy_smtplib import ProxySMTP

import os
import sys
import getopt
import traceback

import json
from collections import defaultdict

import time
from time import strftime
import random

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


# Input: User's changed sites list
# Output: If multiple sites then "[name1] and x more sites have updated!". 
# If one site then "[name1] has updated!"
def sitesToMailSubject(sites):
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
    global defaultEncoding
    
    if encoding is None:
        encoding = defaultEncoding

    mail_content = ''

    if sendAsHtml:
        for site in sites:
            content = '<p><a href="' + site['uri'] + '">' + site['name'] + '</a></p>\n' + site['changes'] + '\n\n'
            mail_content += content
        mail = buildMailBody(subject, mail_content, None, sendAsHtml, encoding)
    else:
        for site in sites:
            content = site['uri'] + '\n' + site['changes'] + '\n\n'
            mail_content += content
        mail = buildMailBody(subject, mail_content, None, sendAsHtml, encoding)

    return mail


# TODO: Render html mail independently as web page. 
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
    if 'changes' in site:
        site = site.copy()
        site.pop('changes')

    file_path = os.path.join(config["workingDirectory"], site["name"] + '.txt')
    with open(file_path, 'w') as thefile:
        thefile.write(json.dumps(site))


# 没有的话就返回空的defaultdict
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


# TODO: Send mail by message queue. 
# TODO: Use MongoDB to save the sites. 
# sites: List with dicts as element. Directly from config.
def pollWebsites(sites):
    global defaultEncoding

    send_dict = {}

    # 每个网站把数据储存在name.txt中，直接把得到的内容与txt文件的全部内容对比
    # 用Mayers算法对比得到全部的变更。所以有parser也可以直接把全部内容放进文件再与之前比对
    
    # 发生变化的时候发邮件，把所有的发生变化的uri放在一个邮件里发出。把新加的或者变更的几行拿出来(git diff的Myers算法)。
    for i, site in enumerate(sites):
        site_name = site['name']
        print('polling site [' + site_name + '] ...')

        try:
            raw_contents = uritool.URLReceiver(uri=site['uri'], contenttype=site['contentType'], userAgent=config['userAgent']).performAction()
            if site['parserType'] and site['path']:
                parser = parsertool.ParserGenerator.getInstance(site['parserType'], site['path'])
                raw_contents = parser.performAction(raw_contents)
        except Exception as e:
            # TODO: Send error mail here. 
            subject = "[Error] " + str(e.code) + " happened when polling " + site_name
            content = str(e.code) + ' ' + e.reason
            mail = buildMailBody(subject, content, link=site['uri'], sendAsHtml=False)
            sendmail([config['administrator']], mail, False)
            continue

        site_previous = getStoredSite(site_name)

        # raw_contents will only have one element in the list. 
        # content is a Content object
        for content in raw_contents:
            # Only send update mail when site file exists and updated. 
            if not site_previous:
                site['content'] = content.content
                storeSite(site)
            # 注意如果name没变，但是parser改变的情况。此时不通知变化，只保存。
            # 文件里按照config的sites中元素形式保存成json文件，多一个content键值对
            elif content.content != site_previous['content']:
                site['content'] = content.content

                storeSite(site)

                # changes = myers.diff(site_previous['content'].splitlines(), content.content.splitlines(), format=True, diffs_only=True)
                changes = myers.get_inserts(site_previous['content'].splitlines(), content.content.splitlines())
                changes = '\n'.join(changes)
                site['changes'] = changes

                # 填充sender_dict，{subscriber:[idx1, idx2]}。
                # idx是subscriber监控sites中发生变化的index
                for subscriber in site['subscribers']:
                    if subscriber in send_dict:
                        send_dict[subscriber].append(i)
                    else:
                        send_dict[subscriber] = [i]

    # Construct mail body and send mail
    # 不同的site monitor的人可能不同。。要以人为单位构建并发送邮件
    
    for subscriber, sites_idxs in send_dict.items():
        changed_subscribed_sites = [sites[i] for i in sites_idxs]

        subject = sitesToMailSubject(changed_subscribed_sites)

        mail = sitesToMail(subject, changed_subscribed_sites)
        sendmail([subscriber], mail, True)


def _main():
    global config

    notiontool.pull_config()
    config = utils.loadConfig()
    sites = config['sites']

    pollWebsites(sites)


if __name__ == '__main__':
    _main()
