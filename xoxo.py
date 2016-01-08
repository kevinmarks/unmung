#!/usr/bin/python
# -*- coding: utf-8 -*-
"""xoxo.py - a utility module for transforming to and from the XHTMLOutlines format XOXO http://microformats.org/wiki/xoxo
toXOXO takes a Python datastructure (tuples, lists or dictionaries, arbitrarily nested) and returns a XOXO representation of it.
fromXOXO parses an XHTML file for a xoxo list and returns the structure
"""
__version__ = "0.9"
__date__ = "2005-11-02"
__author__ = "Kevin Marks <kmarks@technorati.com>"
__copyright__ = "Copyright 2004-2006, Kevin Marks & Technorati"
__license__ = "http://creativecommons.org/licenses/by/2.0/ CC-by-2.0], [http://www.apache.org/licenses/LICENSE-2.0 Apache 2.0"
__credits__ = """Tantek Çelik and Mark Pilgrim for data structure"""
__history__ = """
TODO: add <title> tag
TODO: add a proper profile link
0.9 smarter parsing for encoding and partial markup; fix dangling dictionary case
0.8 work in unicode then render to utf-8
0.7 initial encoding support - just utf-8 for now
0.6 support the special behaviour for url properties  to/from <a>
0.5 fix some awkward side effects of whitespace and text outside our expected tags; simplify writing code
0.4 add correct XHTML headers so it validates
0.3 read/write version; fixed invalid nested list generation;
0.1 first write-only version
"""

try:
    True, False
except NameError:
    True, False = not not 1, not 1
containerTags={'ol':False,'ul':False,'dl':False}
import sgmllib, urllib, urlparse, re,codecs

def toUnicode(key):
    if type(key) == type(u'unicode'):
        uKey= key
    else:
        try: 
            uKey=unicode(key,'utf-8')
        except:
            uKey=unicode(key,'windows_1252')
    return uKey

def makeXOXO(struct,className=None):
    s=u''
    if isinstance(struct,list) or isinstance(struct,tuple):
        if className:
            s += u'<ol class="%s">' % className
        else:
            s+= u"<ol>"
        for item in struct:
            s+=u"<li>" + makeXOXO(item,None)+"</li>"
        s +=u"</ol>"
    elif isinstance(struct,dict):
        d=struct.copy()
        if d.has_key('url') and d['url'] and not isinstance(d['url'],list) and not isinstance(d['url'],dict):
            uURL=toUnicode(d['url'])
            s+=u'<a href="%s" ' % uURL
            text =  d.get('text',d.get('title',uURL))
            for attr in ('title','rel','type'):
                if d.has_key(attr):
                    xVal = makeXOXO(d[attr],None)
                    s +=u'%s="%s" ' % (attr,xVal)
                    del d[attr]
            s +=u'>%s</a>' % makeXOXO(text,None)
            if d.has_key('text'):
                del d['text']
            del d['url']
        if len(d):
            s +=u"<dl>"
            for key,value in d.items():
                xVal = makeXOXO(value,None)
                uKey=toUnicode(key)
                s+= u'<dt>%s</dt><dd>%s</dd>' % (uKey, xVal)
            s +=u"</dl>"
    elif type(struct) == type(u'unicode'):
        s+=struct
    else:
        if not type(struct)==type(' '):
            struct=str(struct)
        s += toUnicode(struct)
    return s
class AttrParser(sgmllib.SGMLParser):
    def __init__(self):
        sgmllib.SGMLParser.__init__(self)
        self.text=[]
        self.encoding='utf-8'
    def cleanText(self,inText):
        if type(inText) == type(u'unicode'):
            inText = inText.encode(self.encoding,'replace')
        self.text=[]
        self.reset()
        self.feed(inText)
        return ''.join(self.text)
    def setEncoding(self,encoding):
        if 'ascii' in encoding:
            encoding='windows_1252' # so we don't throw an exception on high-bit set chars in there by mistake
        if encoding and not encoding =='text/html':
            try:
                canDecode = codecs.getdecoder(encoding)
                self.encoding = encoding
            except:
                try:
                    encoding='japanese.' +encoding
                    canDecode = codecs.getdecoder(encoding)
                    self.encoding = encoding
                except:
                    print "can't deal with encoding %s" % encoding
                    
    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for "&copy;", ref will be "copy"
        # map through to unicode where we can
        try:
            entity =htmlentitydefs.name2codepoint[ref]
            self.handleUnicodeData(unichr(entity))
        except:
            try:
                handle_charref(ref) # deal with char-ref's missing the '#' (see Akma)
            except:
                self.handle_data("&%s" % ref)

    def handle_charref(self, ref):
        # called for each character reference, e.g. for "&#160;", ref will be "160"
        # Reconstruct the original character reference.
        try:
            if ref[0]=='x':
                self.handleUnicodeData(unichr(int(ref[1:],16)))
            else:
                self.handleUnicodeData(unichr(int(ref)))
        except:
            self.handle_data("&#%s" % ref)

# called for each block of plain text, i.e. outside of any tag and
# not containing any character or entity references
    def handle_data(self, text):
        if type(text)==type(u' '):
            self.handleUnicodeData(text)
        if self.encoding== 'utf-8':
            try:
                uText = unicode(text,self.encoding) #utf-8 is pretty clear when it is wrong
            except:
                uText = unicode(text,'windows_1252','ignore') # and this is the likely wrongness
        else:
            uText = unicode(text,self.encoding,'replace') # if they have really broken encoding, (eg lots of shift-JIS blogs)
        self.handleUnicodeData(uText)
    def handleUnicodeData(self, uText):
        self.text.append(uText)
        
class xoxoParser(AttrParser):
    def __init__(self):
        AttrParser.__init__(self)
        self.structs=[]
        self.xostack=[]
        self.textstack=['']
        self.attrparse = AttrParser()
    def normalize_attrs(self, attrs):
        attrs = [(k.lower(), self.attrparse.cleanText(v)) for k, v in attrs]
        attrs = [(k, k in ('rel','type') and v.lower() or v) for k, v in attrs]
        return attrs
    def setEncoding(self,encoding):
        AttrParser.setEncoding(self,encoding)
        self.attrparse.setEncoding(encoding)
    def pushStruct(self,struct):
        if type(struct) == type({}) and len(struct)==0 and len(self.structs) and type(self.structs[-1]) == type({}) and self.structs[-1].has_key('url') and len(self.xostack) and self.structs[-1] != self.xostack[-1]:
            self.xostack.append(self.structs[-1]) # put back the <a>-made one for extra def's
        else:
            self.structs.append(struct)
            self.xostack.append(self.structs[-1])
    def do_meta(self, attributes):
        atts = dict(self.normalize_attrs(attributes))
        #print atts.encode('utf-8')
        if atts.has_key('http-equiv'):
            if atts['http-equiv'].lower() == "content-type":
                if atts.has_key('content'):
                    encoding = atts['content'].split('charset=')[-1]
                    self.setEncoding(encoding)
    def start_a(self,attrs):
        attrsD = dict(self.normalize_attrs(attrs))
        attrsD['url']= attrsD.get('href','')
        if attrsD.has_key('href'):
            del attrsD['href']
        self.pushStruct(attrsD)
        self.textstack.append('')
    def end_a(self):
        val = self.textstack.pop()
        if val: 
            if self.xostack[-1].get('title','') == val:
                val=''
            if self.xostack[-1]['url'] == val:
                val=''
            if val:
                self.xostack[-1]['text']=val
        self.xostack.pop()
    def start_dl(self,attrs):
        self.pushStruct({})
    def end_dl(self):
        self.xostack.pop()
    def start_ol(self,attrs):
        self.pushStruct([])
    def end_ol(self):
        self.xostack.pop()
    def start_ul(self,attrs):
        self.pushStruct([])
    def end_ul(self):
        self.xostack.pop()
    def start_li(self,attrs):
        self.textstack.append('')
    def end_li(self):
        val = self.textstack.pop()
        while ( self.structs[-1] != self.xostack[-1]):
            val = self.structs.pop()
            self.xostack[-1].append(val)
        if type(val) == type(' ') or type(val) == type(u' '):
            self.xostack[-1].append(val)
    def start_dt(self,attrs):
        self.textstack.append('')
    def end_dt(self):
        pass
    def start_dd(self,attrs):
        self.textstack.append('')
    def end_dd(self):
        try:
            val = self.textstack.pop()
            key = self.textstack.pop()
            if self.structs[-1] != self.xostack[-1]:
                val = self.structs.pop()
            self.xostack[-1][key]=val
        except:
            pass
    def handleUnicodeData(self, text):
        if len(self.stack) and containerTags.get(self.stack[-1],True): #skip text not within an element
            self.textstack[-1] += text
def toXOXO(struct,addHTMLWrapper=False,cssUrl=''):
    if type(struct) ==type((1,))or type(struct) ==type([1,]):
        inStruct = struct
    else:
        inStruct = [struct]
    if addHTMLWrapper:
        s= u'''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN
http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"><head profile=""><meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'''
        if cssUrl:
            s+=u'<style type="text/css" >@import "%s";</style>' % cssUrl
        s+=u"</head><body>%s</body></html>" % makeXOXO(inStruct,'xoxo')
        return s.encode('utf-8')
    else:
        return makeXOXO(inStruct,'xoxo').encode('utf-8')
    
def fromXOXO(html):
    parser = xoxoParser()
    #parser.feed(unicode(html,'utf-8'))
    parser.feed(html)
    #print parser.structs
    structs=[struct for struct in parser.structs if struct]
    #print structs
    while (len(structs) ==1 and type(structs)==type([1,])):
        structs=structs[0]
    return structs
