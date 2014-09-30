import os
import urllib2
import feedparser

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
        values ={};
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(values))
        
class Feed(webapp2.RequestHandler):
    def get(self):
        url = self.request.get('feed')
        values = {"url": url, "feed":"no feed found","entries":[],"raw":self.request.get('raw'),"feeds":[url]}
        feedblob = feedparser.parse(url)
        values["feed"] = feedblob["feed"]
        values["entries"] = feedblob["entries"]
        if len(values["entries"]) ==0:
            values["entries"]=["no entries"]
        template = JINJA_ENVIRONMENT.get_template('hfeed.html')
        self.response.write(template.render(values))


class Ello(webapp2.RequestHandler):
    def get(self):
        url = 'https://ello.co/'+self.request.get('ello').strip()+'.json'
        values = {"url": url, "feed":"no user found","raw":self.request.get('raw')}
        result = urlfetch.fetch(url)
        #self.response.write(result.content)
        if result.status_code == 200:
            values["feed"] = json.loads(result.content)
            values["feeds"] = result.content
            values["feed"]["links"] = values["feed"].get("links","").split()
            template = JINJA_ENVIRONMENT.get_template('hfeedello.html')
            self.response.write(template.render(values))
        else:
            self.response.write("%i: %s" % (result.status_code,result.content))

        
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/feed',Feed),
    ('/ello',Ello)
], debug=True)