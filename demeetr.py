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
	raw_time_list = db.ListProperty(str)
	overall_time_chart = db.ListProperty(str)
	confirmed = db.BooleanProperty()

class Option(db.Model):
	title = db.StringProperty()
	description = db.StringProperty()
	place = db.StringProperty()
	duration = db.FloatProperty()
	minimum = db.IntegerProperty()
	votes = db.IntegerProperty()


class HomePage(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			parent_key = db.Key.from_path('User',user.email())
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
			self.redirect(users.create_login_url(self.request.uri))


class Events(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			my_id = int(self.request.get('id'))
			event_key = db.Key.from_path('Event',my_id)
			event = db.get(event_key)

			parent_key = db.Key.from_path('User', user.email())
			person = db.get(parent_key)

			key_list = person.event_key_list

			query = db.GqlQuery("SELECT * "
								"FROM Event "
								"WHERE __key__ IN :1 "
								"ORDER BY created_time ASC",
								 key_list)

			option_query = db.GqlQuery("SELECT * "
										"FROM Option "
										"WHERE ANCESTOR IS :1 "
										"ORDER BY votes DESC",
										event_key)

			total_votes = 0
			for option in option_query:
				total_votes += option.votes
			if total_votes == 0:
				total_votes = 1

			template_values = {
			'total_votes' : total_votes,
			'options' : option_query,
			'user' : person,
			'my_events' : query,
			'event' : event,
			'user_mail' : user.email(),
			'logout' : users.create_logout_url(self.request.host_url)
			}
			template = jinja_environment.get_template('eventhome.html')
			self.response.out.write(template.render(template_values))
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
		event.invitees = [event.creator]
		event.respondents = []
		event.confirmed = False

		event.put()

		person.event_key_list.append(event.key())
		person.put()

		self.redirect('/events?id=' + str(event.key().id()))

class AddOption(webapp2.RequestHandler):
	def post(self):
		event_id = int(self.request.get('event_id'))
		event_key = db.Key.from_path('Event',event_id)
		event = db.get(event_key)

		if event == None:
			self.redirect('/')

		curr_option = Option(parent=event_key)
		curr_option.title = self.request.get('title')
		curr_option.description = self.request.get('desc')
		curr_option.place = self.request.get('place')
		curr_option.duration = float(self.request.get('duration'))
		curr_option.minimum = int(self.request.get('min'))
		curr_option.votes = 0

		curr_option.put()

		self.redirect('/events?id=' + str(event.key().id()))


class Profile(webapp2.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if user:
			user_key = db.Key.from_path('User',user.email())
			our_user = db.get(user_key)
			template_values = {
			'user':our_user,
			'user_mail': user.email(),
			'logout' : users.create_logout_url(self.request.host_url)
			}
			template = jinja_environment.get_template('profile.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect(users.create_login_url(self.request.uri))

class Invite(webapp2.RequestHandler):
	def post(self):
		current_user_key = db.Key.from_path('User',users.get_current_user().email())
		current_user = db.get(current_user_key)

		add_email_list = self.request.get_all('invited[]')
		event_id = int(self.request.get('event_id'))
		event_key = db.Key.from_path('Event',event_id)
		event = db.get(event_key)

		for email in add_email_list:
			add_key = db.Key.from_path('User',email)
			added_user = db.get(add_key)

			added_user.event_key_list.append(event_key)
			added_user.put()

			event.invitees.append(added_user.email)

		event.put()

		self.redirect('/events?id=' + str(event_id))

class AddFriend(webapp2.RequestHandler):
	def post(self):
		current_user_key = db.Key.from_path('User',users.get_current_user().email())
		current_user = db.get(current_user_key)

		add_email = self.request.get('add_email')
		add_key = db.Key.from_path('User',add_email)
		added_user = db.get(add_key)

		current_user.friends_list.append(added_user.email)
		current_user.put()

		added_user.friends_list.append(current_user.email)
		added_user.put()

		self.redirect('/home')


class UserSearch(webapp2.RequestHandler):
	def post(self):

		search_item = self.request.get('search').rstrip()

		search_key = db.Key.from_path('User',search_item)

		target_user = db.get(search_key)

		user_key = db.Key.from_path('User',users.get_current_user().email())

		current_user = db.get(user_key)

		template_values = {
			'target_user': target_user,
			'target': search_item,
			'user_mail': users.get_current_user().email(),
			'current_user': current_user,
			'logout': users.create_logout_url(self.request.host_url),
		}

		template = jinja_environment.get_template('display.html')
		self.response.out.write(template.render(template_values))


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

class Vote(webapp2.RequestHandler):
	def post(self):
		event_id = int(self.request.get('event_id'))
		event_key = db.Key.from_path('Event',event_id)
		option_id = int(self.request.get('option_id'))
		option_key = db.Key.from_path('Option',option_id,parent=event_key)
		option = db.get(option_key)

		option.votes += 1

		option.put()

		self.redirect('/events?id=' + str(event_id))


app = webapp2.WSGIApplication([('/home',HomePage),
								('/messages',Messages),
								('/settings',Settings),
								('/profile',Profile),
								('/events',Events),
								('/search',UserSearch),
								('/invite',Invite),
								('/addoption',AddOption),
								('/addfriend',AddFriend),
								('/eventvote',Vote),
								('/addevent',AddEvent)],
								debug = True)