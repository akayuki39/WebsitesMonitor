# WebsitesMonitor🚀

[![build passing](https://img.shields.io/badge/build-passing-brightgreen)]()
[![GitHub issues](https://img.shields.io/github/issues/akayuki39/WebsitesMonitor)](https://github.com/akayuki39/WebsitesMonitor/issues)
[![GitHub license](https://img.shields.io/github/license/akayuki39/WebsitesMonitor)](https://github.com/akayuki39/WebsitesMonitor/blob/master/LICENSE)

Monitors changes of websites and notify users by email. 


## How to use

Websites Monitor uses a [Notion](https://www.notion.so) database as frontend to configure sites to monitor. This can be helpful when you are using this tool for your team. You need a Notion account and create a database with properties:

* name: Property Type **Title**. 
    * This is the name and id of your websites, make sure they don't duplicate. You
* uri: Property Type **URL**. 
    * URL of the website.
* contentType: Property Type **Select**. 
    * Content type. 'html' / 'plain' / 'xml' etc. 
* path: Property Type **Text** 
    * Parser of the part in the website you want to monitor. Use CSS Selector or XPath. 
* parserType: Property Type **Select**
    * Type of the parser. 'css' or 'xpath'.
* subscribers: Property Type **Person**
    * Users who want to monitor this website. 

Then you need to turn on the Share to web button in Notion and invite your notion integration from [Notion API](https://developers.notion.com). 

If you prefer configure sites manaully, just remove the `notiontool.pull_config()` line in `main.py` and there you go. 


## Configuration
Configurations are in file `config.json`. 

### sites parameters
```jsonc
"sites": [
    {
        "name": "WebsitesMonitor GitHub",
        "uri": "https://github.com/akayuki39/WebsitesMonitor",
        "contentType": "html",
        "parserType": "css",
        "path": ".Layout-main",
        "subscribers": [
            "my-email@gmail.com"
        ]
    }]
```
Parameters are same with the properties from notion. This part is automatically updated from the Notion database. 

### SMTP parameters
```
senderName": "WebsitesMonitor",
sender": "websitesmonitor@email.com",
useTLS": true,
smtphost": "smtphost.com",
smtpport": 587,
smtpusername": "websitesmonitor.noreply",
smtppwd": "password",
administrator": "your-email@email.com",
useSmtpProxy": false,
smtpProxyAddr": "127.0.0.1",
smtpProxyPort": "7890"
```

### Notion parameters
```
"userAgent": "Mozilla/5.0 (Windows NT 6.1; WOW64)",
"notionToken": "your-notion-token",
"notionDatabaseId": "your-notion-database-id"
```

### Other parameters
```
"userAgent": "Mozilla/5.0 (Windows NT 6.1; WOW64)",
"workingDirectory": "/usr/WebsitesMonitor",
```
Your need to change `_CONFIG_PATH` in `utils.py` to your config file's absolute path. 


## Deployment

First your need install Python 3.7 and all the requirements. For ubuntu 18.04, type:
```bash
sudo apt-get install python3 python3-dev python3-setuptools
sudo easy_install3 pip
cd /your-working-directory
sudo pip3 install -r requirements.txt
```

This tool is relying on crontab to function periodically. Add below line to your crontab:
```
0 0-23/2 * * * /usr/bin/python3 /your-working-directory-main.py
```

And there you go! This will make WebsitesMonitor works every 2 hours. 








