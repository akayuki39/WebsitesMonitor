import urllib.parse
from lxml import etree
from cssselect import GenericTranslator
import re
from utils import Content


# Attributes in HTML files storing URI values. These values are automatically translated to absolute URIs.
uriAttributes = [['//img[@src]', 'src'], ['//a[@href]', 'href']]

maxTitleLength = 150


# returns a short subject line
def getSubject(textContent):
    global maxTitleLength
    
    if textContent is None or len(textContent.strip()) == 0:
        return 'Website has been updated'
    textContent = re.sub(' +', ' ', re.sub('\s', ' ', textContent)).strip()
    return (textContent[:maxTitleLength] + ' [..]') if len(textContent) > maxTitleLength else textContent


# translates all relative URIs found in trees to absolute URIs
def toAbsoluteURIs(trees, baseuri):
    global uriAttributes

    for tree in trees:
        if isinstance(tree, str):
            continue
        for uriAttribute in uriAttributes:
            tags = tree.xpath(uriAttribute[0])
            for tag in tags:
                if tag.attrib.get(uriAttribute[1]) is not None:
                    if urllib.parse.urlparse(tag.attrib[uriAttribute[1]]).scheme == '':
                        tag.attrib[uriAttribute[1]] = urllib.parse.urljoin(baseuri, tag.attrib[uriAttribute[1]])


class ParserGenerator():
    """docstring for ParserGenerator"""
    def getInstance(parser_type, parse_path, title_path=None):
        if parser_type == "xpath":
            return XPathParser(parse_path, title_path)
        elif parser_type == "css":
            return CSSParser(parse_path, title_path)
        

class Parser:
    # input: [Content], output: [Content]
    def performAction(self, contentList):
        pass


class XPathParser(Parser):
    def __init__(self, contentxpath, titlexpath=None):
        self.contentxpath = contentxpath
        self.titlexpath = titlexpath

    # input: [Content], output: [Content]
    def performAction(self, contentList):
        result = []
        for content in contentList:
            result.extend(self.parseOneObject(content))
        return result

    # input: Content, output: [Content]
    def parseOneObject(self, content):
        baseuri = content.uri
        if content.contenttype == 'html':
            parser = etree.HTMLParser(encoding=content.encoding)
        else:
            parser = etree.XMLParser(recover=True, encoding=content.encoding)

        tree = etree.fromstring(content.content, parser=parser)

        # xpath
        contentresult = [] if self.contentxpath is None else tree.xpath(self.contentxpath)
        titleresult = [] if self.titlexpath is None else tree.xpath(self.titlexpath)

        # translate relative URIs to absolute URIs
        if content.contenttype == 'html':
            basetaglist = tree.xpath('/html/head/base')
            if len(basetaglist) != 0:
                baseuri = basetaglist[0].attrib['href']
            if len(contentresult) != 0:
                toAbsoluteURIs(contentresult, baseuri)
            if len(titleresult) != 0:
                toAbsoluteURIs(titleresult, baseuri)

        if self.contentxpath and len(contentresult) == 0:
            raise Exception('WARNING: content selector became invalid!')
        if self.titlexpath and len(titleresult) == 0:
            raise Exception('WARNING: title selector became invalid!')

        contents = []
        titles = []
        if isinstance(contentresult, str):
            contents = [contentresult]
        else:
            if len(contentresult) == 0:
                contentresult = titleresult
            contents = [etree.tostring(s, encoding=content.encoding, pretty_print=True).decode(content.encoding, errors='ignore') for s in contentresult]

        if isinstance(titleresult, str):
            titles = [getSubject(titleresult)]*len(contents)
        else:
            if len(titleresult) == 0 or len(titleresult) != len(contentresult):
                titleresult = contentresult
            titles = [getSubject(etree.tostring(s, method='text', encoding=content.encoding).decode(content.encoding, errors='ignore')) for s in titleresult]

        result = []
        for i in range(0, len(contents)):
            result.append(Content(uri=content.uri, encoding=content.encoding, title=titles[i], content=contents[i], contenttype=content.contenttype))

        return result


class CSSParser(Parser):
    def __init__(self, contentcss, titlecss=None):
        contentxpath = GenericTranslator().css_to_xpath(contentcss)
        titlexpath = None
        if titlecss is not None:
            titlexpath = GenericTranslator().css_to_xpath(titlecss)

        self.xpathparser = XPathParser(contentxpath=contentxpath, titlexpath=titlexpath)

    # input: [Content], output: [Content]
    def performAction(self, contentList):
        return self.xpathparser.performAction(contentList)
