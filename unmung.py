import os
import urllib2
import urllib
import feedparser
import datetime
import html5lib
import mf2py
import cassis



import jinja2
import webapp2
import json
from google.appengine.api import urlfetch



JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
    
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
        url = self.request.get('feed')
        values = {"url": url, "feed":"no feed found","entries":[],"raw":self.request.get('raw'),"feeds":[url]}
        feedblob = feedparser.parse(url)
        values["feed"] = feedblob["feed"]
        values["entries"] = feedblob["entries"]
        for entry in values["entries"]:
            if "published" in entry:
                entry["iso_published"] =  datetime.datetime(*entry["published_parsed"][:6]).isoformat()
            if "updated" in entry:
                entry["iso_updated"] = datetime.datetime(*entry["updated_parsed"][:6]).isoformat()
        if len(values["entries"]) ==0:
            values["entries"]=["no entries"]
        template = JINJA_ENVIRONMENT.get_template('hfeed.html')
        self.response.write(template.render(values))

class Microformats(webapp2.RequestHandler):
    def get(self):
        url = self.request.get('url')
        html = self.request.get('html')
        prettyText = self.request.get('pretty','')
        pretty = prettyText == 'on'
        if html:
            self.redirect("/?"+urllib.urlencode({'html':html,'pretty':prettyText}))
        elif url:
            mf2json = mf2py.Parser(doc=urllib2.urlopen(url)).to_json(pretty)
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
    ('/ello',Ello),
    ('/mf2',Microformats),
    ('/autolink',Autolink)

], debug=True)