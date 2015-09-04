import os
import urllib2
import urllib
import feedparser
import datetime
import html5lib
import mf2py
import cassis
import urlparse


import jinja2
import webapp2
import json
import openanything
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.api import taskqueue

import logging

useragent = 'IndieWebCards/0.5 like Mozilla'

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

def fixurl(url):
    if url:
        if "://" not in url:
            url = "http://"+url
    if "twitter.com" in url and '/intent/' not in url:
        urlbits= list(urlparse.urlsplit(url))
        urlbits[3] = urllib.urlencode({"screen_name": urlbits[2][1:]})
        urlbits[2] = '/intent/user'
        url=urlparse.urlunsplit(urlbits)
    return url


def mf2parseWithCaching(url,fetch=False):
    etag = memcache.get(url,namespace='ETag')
    lastmod = memcache.get(url,namespace='Last-Modified')
    reuse = memcache.get(url,namespace='reuse')
    mf2 = memcache.get(url,namespace='mf2')
    params={}
    logging.info("mf2parseWithCaching: url '%s' etag '%s' lastmod '%s' reuse=%s fetch=%s mf2='%s'" % (url, etag, lastmod,reuse, fetch, str(mf2)[:30]))
    if fetch or not mf2:
        if not mf2:
            # need to actually fetch the URL
            etag,lastmod,reuse = None,None,None
        if etag or lastmod:
            # if they're nice enough to support these, respect their updated state
            reuse=None
        if not reuse:
            try:
                params = openanything.fetch(url, etag, lastmod, useragent)
            except Exception,e:
                logging.info("mf2parseWithCaching: openanything '%s' fail '%s' " % (params,e))
        else:
            logging.info("mf2parseWithCaching: - reuse '%s'"  % (url))
        if params.get('status') == 304 or params.get('data','') == '' and not reuse:
            logging.info("mf2parseWithCaching: - using cached '%s'"  % (url))
        else:
            mf2=None #reparse and set cache
            logging.info("mf2parseWithCaching: - forcing reparse '%s'"  % (url))
    else:
        taskurl = '/refreshmf2cache/'+urllib.quote(url)
        logging.info("mf2parseWithCaching: - queing task '%s'"  % (taskurl))
        taskqueue.add(url=taskurl)
    if mf2 is None and params:
        logging.info("mf2parseWithCaching: - parsing '%s'"  % (url))
        mf2 = mf2py.Parser(params.get('data',''), url=url).to_dict()
        memcache.set(url,mf2,namespace='mf2')
        etag = params.get('etag')
        memcache.set(url,etag,namespace='ETag')
        lastmod = params.get('lastmodified')
        memcache.set(url,lastmod,namespace='Last-Modified')
        logging.info("mf2parseWithCaching: setting memcache  etag '%s' lastmod '%s'" % ( etag, lastmod))
        memcache.set(url,'reuse',time=3600,namespace='reuse')
    return mf2
    
class RefreshMF2Cache(webapp2.RequestHandler):
    def post(self,url):
        url = urllib.unquote(url)
        logging.info("RefreshMF2Cache: '%s'"  % (url))
        mf2parseWithCaching(url,fetch=True)
        self.response.write("OK") 

class MainPage(webapp2.RequestHandler):
    def get(self):
        html = self.request.get('html')
        pretty = self.request.get('pretty','on') == 'on'
        rawtext = self.request.get('rawtext')
        embed = self.request.get('embed','')
        maxUrlLength = self.request.get('maxurllength','0')
        if maxUrlLength=='':
            maxUrlLength= '0'
        embedit = embed == 'on'
        values ={"rawhtml": html, "mfjson":"","rawtext":rawtext,"linkedhtml":""}
        if html:
            mf2json = mf2py.Parser(doc=html).to_json(pretty)
            values["mfjson"] = mf2json
        if rawtext:
            linkedhtml = cassis.auto_link(rawtext,do_embed=embedit,maxUrlLength=int(maxUrlLength))
            values["linkedhtml"] = linkedhtml
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(values))
        
class Feed(webapp2.RequestHandler):
    def get(self):
        url = fixurl(self.request.get('feed'))
        values = {"url": url, "feed":"no feed found","entries":[],"raw":self.request.get('raw'),"feeds":[url]}
        feedblob = feedparser.parse(url)
        values["feed"] = feedblob["feed"]
        values["entries"] = feedblob["entries"]
        for entry in values["entries"]:
            if "published" in entry and entry["published_parsed"]:
                entry["iso_published"] =  datetime.datetime(*entry["published_parsed"][:6]).isoformat()
            if "updated" in entry and entry["updated_parsed"]:
                entry["iso_updated"] = datetime.datetime(*entry["updated_parsed"][:6]).isoformat()
        if len(values["entries"]) ==0:
            values["entries"]=["no entries"]
        template = JINJA_ENVIRONMENT.get_template('hfeed.html')
        self.response.write(template.render(values))

class IndieCard(webapp2.RequestHandler):
    def get(self):
        url = fixurl(self.request.get('url'))
        values={"url":url}
        mf2 = mf2parseWithCaching(url)
        for item in mf2["items"]:
            if not item["type"][0].startswith('h-x-'):
                values["item"]= item
                break
        template = JINJA_ENVIRONMENT.get_template('indiecard.html')
        self.response.write(template.render(values))

class MultiTest(webapp2.RequestHandler):
    def get(self):
        urls =["http://kevinmarks.com"]*20
        template = JINJA_ENVIRONMENT.get_template('hovertest.html')
        values={"urls":urls}
        self.response.write(template.render(values))


class HoverTest(webapp2.RequestHandler):
    def get(self):
        urls =["http://werd.io","http://kevinmarks.com","http://tantek.com",
        "http://chocolateandvodka.com/","https://kylewm.com/","https://snarfed.org/",
        "http://laurelschwulst.com/","http://pmckay.com","http://giudici.us/",
        "http://cascadesf.com/","http://kathyems.wordpress.com/",
        "http://www.katiejohnson.me/whatimthinking.html","http://ma.tt",
        "http://known.kevinmarks.com","http://epeus.blogspot.com","https://plus.google.com/+KevinMarks",
        "http://twitter.com/kevinmarks",'http://about.me/thisisdeb','http://rickydesign.me/',
        'http://www.unmung.com/feed?feed=https%3A%2F%2Fkathyems.wordpress.com%2Ffeed%2F',]
        template = JINJA_ENVIRONMENT.get_template('hovertest.html')
        values={"urls":urls}
        self.response.write(template.render(values))

class HoverCard(webapp2.RequestHandler):
    #like indiecard but to be iframed
    def get(self):
        url = fixurl(self.request.get('url'))
        values={"url":url}
        mf2 = mf2parseWithCaching(url)
        for item in mf2["items"]:
            if item["type"][0].startswith('h-card'):
                values["item"]= item
                break
        if "item" not in values:
            for item in mf2["items"]:
                if "author" in item["properties"] and item["properties"]["author"][0]["type"][0].startswith('h-card'):
                    values["item"]= item["properties"]["author"][0]
                    break
        if "item" not in values:
            values["item"] = {"properties":{"url":[url],"name":[url]},"type":["h-card"]}
        template = JINJA_ENVIRONMENT.get_template('hovercard.html')
        self.response.write(template.render(values))

def findCardFeedEntries(item,hcard,hfeed,hentries):
    if not hcard and item["type"][0].startswith('h-card'):
        hcard = item
    if not hcard and "author" in item["properties"] and item["properties"]["author"][0]["type"][0].startswith('h-card'):
        hcard= item["properties"]["author"][0]
    if not hfeed and item["type"][0].startswith('h-feed'):
        hfeed=item
    if item["type"][0].startswith('h-entry'):
        hentries.append(item)
    return hcard,hfeed,hentries

def getTextOrHTML(item):
    if len(item) <1:
        return '' 
    if type(item[0]) is dict:
        return item[0]["html"]
    else:
        return " ".join(item)

def getTextOrValue(item):
    if len(item) <1:
        return '' 
    if type(item[0]) is dict:
        return item[0]["value"]
    else:
        return " ".join(item)
        
def getTextOrHcard(item):
    if len(item) <1:
        return '' 
    if type(item[0]) is dict:
        html = item[0].get("html","")
        if html:
             return html
        elif "h-card" in item[0].get("type",[]):
            url = getTextOrValue(item[0]["properties"].get("url",[]))
            name = getTextOrValue(item[0]["properties"].get("name",[]))
            return '<a href="%s">%s</a>' % (url,name)
        else:
            return item[0]["value"]
    else:
        return item[0]


class HoverCard2(webapp2.RequestHandler):
    #like indiecard but to be iframed
    def get(self):
        url = fixurl(self.request.get('url'))
        values= {"url": url,
            "banner":"",
            "photo":"",
            "name":url,
            "summary":"",
            "entries":[],
            }
        mf2 = mf2parseWithCaching(url)
        hcard=None
        hfeed=None
        hentries=[]
        if mf2:
            for item in mf2["items"]:
                hcard,hfeed,hentries = findCardFeedEntries(item,hcard,hfeed,hentries)
                for subitem in item.get("children",[]):
                    hcard,hfeed,hentries = findCardFeedEntries(subitem,hcard,hfeed,hentries)
            if hfeed:
                if hfeed["properties"].get("summary"):
                   values["summary"] = getTextOrHTML(hfeed["properties"].get("summary"))
                if not hentries:
                    for item in hfeed.get("children",[]):
                        hcard,hfeed,hentries = findCardFeedEntries(item,hcard,hfeed,hentries)
            if hentries:
                entries=[]
                for entry in hentries[:2]:
                    entries.append({"name":getTextOrValue(entry["properties"].get("name",[])),
                                    "summary": getTextOrHTML(entry["properties"].get("summary",[])),
                                    "url":entry["properties"].get("url",[""])[0]})
                values["entries"] = entries
            if hcard:
                values["name"] = getTextOrHTML(hcard["properties"].get("name",[]))
                if hcard["properties"].get("photo"):
                    values["photo"] = hcard["properties"].get("photo")[0]
                if  hcard["properties"].get("note"):
                    values["summary"] = getTextOrHTML(hcard["properties"].get("note"))
                if  hcard["properties"].get("summary"):
                    values["summary"] = getTextOrHTML(hcard["properties"].get("summary"))
                if  hcard["properties"].get("org"):
                    values["org"] = getTextOrHcard(hcard["properties"].get("org"))
        if values["name"] == url:
            template = JINJA_ENVIRONMENT.get_template('shrunkensite.html')
        else:
            template = JINJA_ENVIRONMENT.get_template('hovercard2.html')
        self.response.headers["Cache-Control"] = "public, max-age=600"
        logging.info(self.response.headers)
        self.response.write(template.render(values))



class Microformats(webapp2.RequestHandler):
    def get(self):
        url = fixurl(self.request.get('url'))
        html = self.request.get('html')
        prettyText = self.request.get('pretty','')
        pretty = prettyText == 'on'
        if html:
            self.redirect("/?"+urllib.urlencode({'html':html,'pretty':prettyText}))
        elif url:
            mf2 = mf2parseWithCaching(url)
            if pretty:
                mf2json = json.dumps(mf2,indent=4, separators=(', ', ': '))
            else:
                mf2json = json.dumps(mf2)
            #mf2json = mf2py.Parser(doc=urllib2.urlopen(url), url=url).to_json(pretty)
            self.response.headers['Content-Type'] = 'application/json'
            self.response.write(mf2json)

class Autolink(webapp2.RequestHandler):
    def get(self):
        rawtext = self.request.get('rawtext').encode('utf-8')
        embed = self.request.get('embed','on')
        maxUrlLength = self.request.get('maxurllength','0')
        if maxUrlLength=='':
            maxUrlLength= '0'
        embedit = embed == 'on'
        self.redirect("/?"+urllib.urlencode({'rawtext':rawtext,'embed':embed,'maxurllength':maxUrlLength}))


class Ello(webapp2.RequestHandler):
    def get(self):
        url = 'https://ello.co/'+self.request.get('ello').strip()+'.json'
        values = {"url": url, "feed":"no user found","raw":self.request.get('raw')}
        result = urlfetch.fetch(url)
        #self.response.write(result.content)
        if result.status_code == 200:
            values["feed"] = json.loads(result.content)
            values["feeds"] = json.dumps(values["feed"],sort_keys=True,indent=2)
            values["feed"]["links"] = values["feed"].get("links","").split()
            template = JINJA_ENVIRONMENT.get_template('hfeedello.html')
            self.response.write(template.render(values))
        else:
            self.response.write("%i: %s" % (result.status_code,result.content))

        
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/feed',Feed),
    ('/indiecard',IndieCard),
    ('/hovercard',HoverCard2),
    ('/ello',Ello),
    ('/mf2',Microformats),
    ('/autolink',Autolink),
    ('/hc2',HoverCard),
    ('/hovertest',HoverTest),
    ('/multitest',MultiTest),
    ('/refreshmf2cache/(.*)',RefreshMF2Cache),
    

], debug=True)