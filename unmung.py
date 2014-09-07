import os
import urllib2
import feedparser

import jinja2
import webapp2


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
        values = {"url": url, "feed":"no feed found","entries":[]}
        try:
            feedblob = feedparser.parse(url)
            values["feed"] = feedblob["feed"]
            values["entries"] = feedblob["entries"]
        except urllib2.URLError,e:
            values["feed"] = e
            pass
        template = JINJA_ENVIRONMENT.get_template('hfeed.html')
        self.response.write(template.render(values))
        
application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/feed',Feed),
], debug=True)