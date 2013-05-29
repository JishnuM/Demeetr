#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os

jinja_environment = jinja2.Environment( 
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + "/templates") )

class FrontPage(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('front.html')
        self.response.out.write(template.render())

class About(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('about.html')
        self.response.out.write(template.render())

class Contact(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('contact.html')
        self.response.out.write(template.render())

class Help(webapp2.RequestHandler):
	def get(self):
		template = jinja_environment.get_template('help.html')
		self.response.out.write(template.render())

class Userhome(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('userhome.html')
        self.response.out.write(template.render())

class Events(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('eventhome.html')
        self.response.out.write(template.render())

class Settings(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('usersettings.html')
        self.response.out.write(template.render())

class Messages(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('usermsgs.html')
        self.response.out.write(template.render())

app = webapp2.WSGIApplication([
    ('/', FrontPage),
    ('/about', About),
    ('/contact',Contact),
    ('/help',Help),
    ('/home', Userhome),
    ('/events', Events),
    ('/settings', Settings),
    ('/messages', Messages)
], debug=True)
