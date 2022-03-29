#!/usr/bin/python3

import urllib.request
import urllib.error
import ssl
from utils import Content


# Disable ssl certificate verify. 
ssl._create_default_https_context = ssl._create_unverified_context


class Receiver():
    def __init__(self, uri):
        self.uri = uri


# Returns: list with only one Content object. [Content]. 
class URLReceiver(Receiver):
    def __init__(self, uri, contenttype='html', encoding='utf-8', userAgent=None, accept=None):
        super().__init__(uri)
        self.contenttype = contenttype
        self.encoding = encoding
        self.userAgent = userAgent
        self.accept = accept

    # input: [Content], output: [Content]
    def performAction(self, contentList=None):
        if contentList is None:
            contentList = []
        
        # open website
        req = urllib.request.Request(self.uri)
        if self.userAgent is not None:
            req.add_header('User-Agent', self.userAgent)
        if self.accept is not None:
            req.add_header('Accept', self.accept)

        with urllib.request.urlopen(req) as thefile:
            filecontent = thefile.read().decode(self.encoding, errors='ignore')
            contentList.append(Content(uri=self.uri, encoding=self.encoding, title=None, content=filecontent, contenttype=self.contenttype))

        return contentList


def _main():
    pass

if __name__ == '__main__':
    _main()