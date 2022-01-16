from collections import namedtuple
import sys
import json


_CONFIG_PATH = 'config.json'


def loadConfig():
    with open(_CONFIG_PATH) as json_file:
        config = json.load(json_file)
    return config


def rewriteConfig(content):
    with open(_CONFIG_PATH, 'w') as thefile:
        thefile.truncate(0)
        thefile.write(content)


class Content:
    def __init__(self, uri, encoding, title, content, contenttype, additional=None, receivers=None):
        self.uri = uri
        self.encoding = encoding
        self.title = title
        self.content = content
        self.contenttype = contenttype
        self.additional = additional
        self.receivers = receivers


def main():
    pass

if __name__ == '__main__':
    sys.exit(main())
