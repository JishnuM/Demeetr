import webapp2
import jinja2
import os
import datetime

from google.appengine.api import users
from google.appengine.ext import db

jinja_environment = jinja2.Environment(
	loader = jinja2.FileSystemLoader(os.path.dirname(__file__) + "/templates"))

# DataStore definitions

class User(db.Model):
	email = db.EmailProperty()
		# Replace with db.EmailProperty later)
	event_key_list = db.ListProperty(db.Key)
	friends_list = db.ListProperty(db.Email)
	name = db.StringProperty()


class Event(db.Model):
	creator = db.EmailProperty()
	created_time = db.DateTimeProperty(auto_now_add=True)
	title = db.StringProperty()
	invitees = db.ListProperty(db.Email)
	respondents = db.ListProperty(db.Email)
	best_place = db.StringProperty()
	best_time = db.DateTimeProperty()
	time_window_start = db.StringProperty()
	time_window_end = db.StringProperty()
	place_list = db.ListProperty(str)
	place_vote_list = db.ListProperty(int)
	raw_time_list = db.ListProperty(str)
	overall_time_chart = db.ListProperty(str)

class HomePage(webapp2.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      	parent_key = db.Key.from_path('User', user.email())
      	person = db.get(parent_key)
    	if person == None:
      		newPerson = User(key_name=user.email())
      		newPerson.email = user.email()
      		newPerson.name = user.nickname()
      		newPerson.friends_list = []
      		newPerson.event_key_list = []
      		newPerson.put()
      	person = db.get(parent_key)

      	key_list = person.event_key_list

      	query = db.GqlQuery("SELECT * "
      						"FROM Event "
      						"WHERE __key__ IN :1 "
      						"ORDER BY created_time ASC",
      						 key_list)


      	template_values = {
      	'my_events' : query,
        'user_mail': user.email(),
        'logout': users.create_logout_url(self.request.host_url),
        } 
      	template = jinja_environment.get_template('userhome.html')
      	self.response.out.write(template.render(template_values))
    else:
      	self.redirect(self.request.host_url)

class Events(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			template = jinja_environment.get_template('eventhome.html')
			self.response.out.write(template.render())
		else:
			self.redirect(users.create_login_url(self.request.uri))

class AddEvent(webapp2.RequestHandler):
	def post(self):
		parent_key = db.Key.from_path('User',users.get_current_user().email())
		person = db.get(parent_key)
		if person == None:
			self.redirect('/')

		event = Event()
		event.title = self.request.get('event_title')
		event.time_window_start = self.request.get('start')
		event.time_window_end = self.request.get('end')
		event.creator = users.get_current_user().email()
		event.put()

		person.event_key_list.append(event.key())
		person.put()

		self.redirect('/home')



class Settings(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			template_values = {
			'user_mail': user.email(),
			'logout' : users.create_logout_url(self.request.host_url)
			}
			template = jinja_environment.get_template('usersettings.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))

class Messages(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			template_values = {
			'user_mail': user.email(),
			'logout' : users.create_logout_url(self.request.host_url)
			}
			template = jinja_environment.get_template('usermsgs.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))







app = webapp2.WSGIApplication([('/home',HomePage),
								('/messages',Messages),
								('/settings',Settings),
								('/events',Events),
								('/addevent',AddEvent)],
								debug = True)