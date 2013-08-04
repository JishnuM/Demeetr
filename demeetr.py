import webapp2
import time
import jinja2
import os
import datetime
import urllib
import cgi
import json
import logging
import gviz_api

# from google.appengine.api import users
from google.appengine.ext import db
from apiclient import discovery
from oauth2client import client
# from oauth2client import crypt
from oauth2client import appengine

from webapp2_extras import security
from webapp2_extras import auth
from webapp2_extras import sessions

jinja_environment = jinja2.Environment(
	loader = jinja2.FileSystemLoader(os.path.dirname(__file__) + "/templates"))

#CONSTANTS

FACEBOOK_APP_ID = 159729634211589
FACEBOOK_APP_SECRET = '5cc790402a831637da35937603ee4f33'
GOOGLE_CLIENT_ID = '1014009831090.apps.googleusercontent.com'
#GOOGLE_CLIENT_ID = '1014009831090-nq72ibol7m6qhbq8rjtfiejjav2qoq7c.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'Sa5QaY3r1bwH8SqrDu2JR-ft'
#GOOGLE_CLIENT_SECRET = 'Mj2mHjEmsvUx4NmeUWRbl-C4'
local = "http://localhost:8080"
server = 'https://demeetr.appspot.com'
# Model definitions

class UserToken(db.Model):

	created = db.DateTimeProperty(auto_now_add=True)
	updated = db.DateTimeProperty(auto_now=True)
	user = db.StringProperty(required=True, indexed=False)
	subject = db.StringProperty(required=True)
	token = db.StringProperty(required=True)

	@classmethod
	def get_key(cls, user, subject, token):
		string = "%s.%s.%s" %(str(user),subject,token)
		return db.Key.from_path('User',string)

	@classmethod
	def create(cls, user, subject, token=None):
		user = str(user)
		token = token or security.generate_random_string(entropy=128)
		key_name = "%s.%s.%s" %(user,subject,token)
		new_entity = cls(key_name=key_name, user=user, subject=subject, token=token)
		new_entity.put()
		return new_entity

	@classmethod
	def get(cls, user=None, subject=None, token=None):
		if user and subject and token:
			return cls.get_key(user,subject,token).get()

		assert subject and token, \
		'subject and token must be provided to UserToken.get().'
		query = db.GqlQuery("SELECT * "
												"FROM :1 "
												"WHERE subject = :2 AND token = :3",
												cls, subject, token)
		return query.get()

class User(db.Model):
	token_model = UserToken

	email = db.EmailProperty()
	event_key_list = db.ListProperty(db.Key)
	friends_list = db.ListProperty(db.Email)
	received_request_list = db.ListProperty(db.Email)
	sent_request_list = db.ListProperty(db.Email)
	name = db.StringProperty()
	created = db.DateTimeProperty(auto_now_add=True)
	updated = db.DateTimeProperty(auto_now=True)
	password = db.StringProperty()
	auth_id = db.StringProperty()
	fb_token = db.StringProperty()
	all_start = db.ListProperty(datetime.datetime)
	all_end = db.ListProperty(datetime.datetime)
	all_content = db.ListProperty(str)
	all_group = db.ListProperty(str)
	all_className = db.ListProperty(str)
	total_events = db.IntegerProperty()


	def get_id(self):
		return self.key().id_or_name()

	def add_auth_id(self, auth_id):
		self.auth_id = auth_id
		self.put()
		return (True, self)

	@classmethod
	def get_by_auth_id(cls, auth_id):
		# query = db.GqlQuery("SELECT * "
		# 										"FROM User"
		# 										"WHERE auth_id = :1",
		# 										auth_id)

		# return query.get()
		key = db.Key.from_path('User',auth_id)
		return db.get(key)

	@classmethod
	def get_by_auth_token(cls, user_id, token, subject='auth'):
		token_key = cls.token_model.get_key(user_id,subject,token)
		user_key = db.Key.from_path('User',user_id)

		valid_token = db.get(token_key)
		user = db.get(user_key)

		if valid_token and user:
			timestamp = int(time.mktime(valid_token.created.timetuple()))
			return user, timestamp

		return None, None

	@classmethod
	def get_by_auth_password(cls, auth_id, password):
		user = cls.get_by_auth_id(auth_id)
		if user == None:
			raise auth.InvalidAuthIdError()

		if not security.check_password_hash(password, user.password):
			raise auth.InvalidPasswordError()

		return user

	@classmethod
	def validate_token(cls, user_id, subject, token):
		query = db.GqlQuery("SELECT * "
							"FROM :1 "
							"WHERE user = :2 AND subject = :3 AND token = :4",
							'User', user_id, subject, token)
		return query.get() is not None
	
	@classmethod
	def create_auth_token(cls, user_id):
		return cls.token_model.create(user_id,'auth').token

	@classmethod
	def validate_auth_token(cls, user_id, token):
		return cls.validate_token(user_id, 'auth', token)

	@classmethod
	def delete_auth_token(cls, user_id, token):
		key = cls.token_model.get_key(user_id, 'auth', token)
		db.delete(key)

	@classmethod
	def create_signup_token(cls, user_id):
		return cls.token_model.create(user_id,'signup').token

	@classmethod
	def validate_signup_token(cls, user_id, token):
		return cls.validate_token(user_id, 'signup', token)

	@classmethod
	def delete_signup_token(cls, user_id, token):
		key = cls.token_model.get_key(user_id, 'signup', token)
		db.delete(key)

	@classmethod
	def set_password(self, raw_password):
		self.password = security.generate_password_hash(raw_password, length=12)


class Event(db.Model):
	creator = db.EmailProperty()
	created_time = db.DateTimeProperty(auto_now_add=True)
	title = db.StringProperty()
	invitees = db.ListProperty(db.Email)
	respondents = db.ListProperty(db.Email)
	best_option_key = db.ReferenceProperty()
	best_time = db.DateTimeProperty()
	time_window_start = db.DateTimeProperty()
	time_window_end = db.DateTimeProperty()
	raw_time_list = db.ListProperty(str)
	overall_start = db.ListProperty(datetime.datetime)
	overall_end = db.ListProperty(datetime.datetime)
	overall_content = db.ListProperty(str)
	overall_group = db.ListProperty(str)
	overall_className = db.ListProperty(str)
	total_times = db.IntegerProperty()
	confirmed = db.BooleanProperty()

class Option(db.Model):
	title = db.StringProperty()
	description = db.StringProperty()
	place = db.StringProperty()
	duration = db.FloatProperty()
	minimum = db.IntegerProperty()
	votes = db.IntegerProperty()
	voters = db.ListProperty(db.Email)
	satisfied = db.BooleanProperty()

class Post(db.Model):
	content = db.StringProperty()
	author = db.StringProperty()
	created_time = db.DateTimeProperty(auto_now_add=True)

class BaseHandler(webapp2.RequestHandler):
	def auth(self):
		return auth.get_auth()

	def user_info(self):
		return self.auth().get_user_by_session()

	def get_user(self):
		info = self.user_info()
		user_key = db.Key.from_path('User',info['email'])
		our_user = db.get(user_key)
		return our_user

	def user_model(self):
		return self.auth().store.user_model

	def session(self):
		return self.session_store.get_session(backend="datastore")

	def dispatch(self):
		self.session_store = sessions.get_store(request=self.request)

		try:
			webapp2.RequestHandler.dispatch(self)
		finally:
			self.session_store.save_sessions(self.response)

# def user_required(handler):
# 	def check_login(self, *args, **kwargs):
# 		auth = self.auth
# 		if not auth.get_user_by_session():
# 			self.redirect('/')
# 		else:
# 			return handler(self,*args,**kwargs)

# 	return check_login


class Signup(BaseHandler):
	def get(self):
		self.redirect('/')
	def post(self):
		username = self.request.get('username')
		email = self.request.get('email')
		password = self.request.get('password')

		test_key = db.Key.from_path('User',email)
		test_user = db.get(test_key)
		if test_user == None:
			newUser = User(key_name = email)
			newUser.email = email
			newUser.name = username
			newUser.password = security.generate_password_hash(password,length=12)
			newUser.friends_list = []
			newUser.event_key_list = []
			newUser.auth_id = email
			newUser.total_events = 0
			newUser.put()

			# user_id = newUser.get_id()

			# token = self.user_model.create_signup_token(user_id)

			u = self.auth().get_user_by_password(email,password,remember=True)

			self.redirect('/home')
		else:
			self.redirect('/?src=fail_signup')

class Login(BaseHandler):
	def get(self):
		self.redirect('/')
	def post(self):
		email = self.request.get('email')
		password = self.request.get('password')
		try:
			u = self.auth().get_user_by_password(email,password,remember=True)
			self.redirect('/home')
		except (auth.InvalidAuthIdError, auth.InvalidPasswordError) as e:
			self.redirect('/?src=fail_login')

class Logout(BaseHandler):
	def get(self):
		self.auth().unset_session()
		self.redirect('/')		

class HomePage(BaseHandler):
	def get(self):

		if self.user_info():
			user = self.get_user()
			key_list = user.event_key_list
			query = db.GqlQuery("SELECT * "
								"FROM Event "
								"WHERE __key__ IN :1 "
								"ORDER BY created_time ASC",
								 key_list)
			template_values = {
			'my_events' : query,
			'user': user,
			}
			template = jinja_environment.get_template('userhome.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect('/unauth')

class Events(BaseHandler):
	def get(self):
		if self.user_info():
			my_id = int(self.request.get('id'))
			event_key = db.Key.from_path('Event',my_id)
			event = db.get(event_key)

			# parent_key = db.Key.from_path('User', user.email())
			# user = db.get(parent_key)
			user = self.get_user()

			key_list = user.event_key_list

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

			post_query = db.GqlQuery("SELECT * "
										"FROM Post "
										"WHERE ANCESTOR IS :1 "
										"ORDER BY created_time ASC",
										 event_key)

			satisfied = []
			for option in option_query:
				if option.satisfied:
					satisfied.append(option)
			if satisfied:
				event.confirmed = True
				best_option = satisfied[0]
				event.best_option_key = best_option.key()
			else:
				event.confirmed = False
				event.best_option_key = None
				best_option = None
			event.put()

			can_vote = []
			for option in option_query:
				if user.email in option.voters:
					can_vote.append(False)
				else:
					can_vote.append(True)

			total_votes = 0
			for option in option_query:
				total_votes += option.votes
			if total_votes == 0:
				total_votes = 1

			description =  [("start", "datetime"),
							("end", "datetime"),
							("content", "string"),
							("group", "string"),
							("className", "string")]
			data = []
			# to get values from datastore into data

			for iterator in range(0, event.total_times):
				temp_start = event.overall_start[iterator]
				temp_end = event.overall_end[iterator]
				temp_content = event.overall_content[iterator]
				temp_group = event.overall_group[iterator]
				temp_className = event.overall_className[iterator]
				temp_event = [temp_start, temp_end, temp_content, temp_group, temp_className]
				data.append(temp_event)

			# for debugging purposes
			# test1 = datetime.datetime(2013, 8, 1, 15, 23, 25)
			# test2 = datetime.datetime(2013, 8, 2, 11, 23, 25)
			# test3 = datetime.datetime(2013, 8, 1, 10, 2, 25)
			# test1e = datetime.datetime(2013, 8, 2, 15, 23, 25)
			# test2e = datetime.datetime(2013, 8, 3, 11, 23, 25)
			# test3e = datetime.datetime(2013, 8, 2, 10, 2, 25)
			# data = [[test1, test1e, "Unavailable", "1st", "unavailable"],
			# 		[test2, test2e, "Available", "2st", "available"],
			# 		[test3, test3e, "Maybe", "3st", "maybe"]]

			# Loading it into gviz_api.DataTable
			data_table = gviz_api.DataTable(description)
			data_table.LoadData(data)

			json = data_table.ToJSon(columns_order=("start", "end", "content", "group", "className"),
			                          order_by="group")

			#for owntimetable
			data_own = []

			for iterator_own in range(0, user.total_events):
				user_start = user.all_start[iterator_own]
				user_end = user.all_end[iterator_own]
				user_content = user.all_content[iterator_own]
				user_group = user.all_group[iterator_own]
				user_className = user.all_className[iterator_own]
				user_event = [user_start, user_end, user_content, user_group, user_className]
				data_own.append(user_event)

			# Loading it into gviz_api.DataTable
			data_table_own = gviz_api.DataTable(description)
			data_table_own.LoadData(data_own)

			# Creating a JSon string
			json_own = data_table_own.ToJSon(columns_order=("start", "end", "content", "group", "className"),
			                          order_by="group")

			template_values = {
			'json' : json,
			'json_own' :json_own,
			'total_votes' : total_votes,
			'options' : option_query,
			'user' : user,
			'my_events' : query,
			'event' : event,
			'user_mail' : user.email,
			'can_vote' : can_vote,
			'posts' : post_query,
			'best': best_option
			# 'logout' : users.create_logout_url(self.request.host_url)
			}
			template = jinja_environment.get_template('eventhome.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect('/unauth')
		# else:
		# 	self.redirect(users.create_login_url(self.request.uri))

class AddEvent(BaseHandler):
	def post(self):
		# parent_key = db.Key.from_path('User',users.get_current_user().email())
		# user = db.get(parent_key)
		# if user == None:
		# 	self.redirect('/')
		if self.user_info():
			user = self.get_user()
			event = Event()
			event.title = self.request.get('event_title')
			
			datetime_start = datetime.datetime.strptime((self.request.get('start')), '%d/%m/%Y %H:%M:%S')
			datetime_end = datetime.datetime.strptime((self.request.get('end')), '%d/%m/%Y %H:%M:%S')

			event.time_window_start = datetime_start
			event.time_window_end = datetime_end
			event.creator = user.email
			event.invitees = [event.creator]
			event.respondents = []
			event.total_times = 0
			event.confirmed = False

			event.put()

			user.event_key_list.append(event.key())
			user.put()

			self.redirect('/events?id=' + str(event.key().id()))
		else:
			self.redirect('/unauth')

class AddAvailability(BaseHandler):
	def post(self):
		if self.user_info():
			my_id = int(self.request.get('id'))
			event_key = db.Key.from_path('Event',my_id)
			event = db.get(event_key)

			if event == None:
				self.redirect('/')

			user = self.get_user()
			datetime_start = datetime.datetime.strptime((self.request.get('start_avail')), '%d/%m/%Y %H:%M:%S')
			datetime_end = datetime.datetime.strptime((self.request.get('end_avail')), '%d/%m/%Y %H:%M:%S')

			#event
			event.overall_start.append(datetime_start)
			event.overall_end.append(datetime_end)
			event.overall_content.append(self.request.get('availability'))
			event.overall_group.append(user.name)
			event.overall_className.append(self.request.get('availability'))
			event.total_times += 1

			#user
			user.all_start.append(datetime_start)
			user.all_end.append(datetime_end)
			user.all_content.append(self.request.get('availability'))
			user.all_group.append(user.name)
			user.all_className.append(self.request.get('availability'))
			user.total_events += 1

			self.redirect('/events?id=' + str(event.key().id()))
		else:
			self.redirect('/unauth')


class AddOption(BaseHandler):
	def post(self):
		if self.user_info():
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
			curr_option.satisfied = (curr_option.votes >= curr_option.minimum)

			curr_option.put()

			self.redirect('/events?id=' + str(event.key().id()))
		else:
			self.redirect('/unauth')

class AddPost(BaseHandler):
	def post(self):
		if self.user_info():
			user = self.get_user()

			event_id = int(self.request.get('event_id'))
			event_key = db.Key.from_path('Event',event_id)
			event = db.get(event_key)

			if event == None:
				self.redirect('/')

			curr_post = Post(parent=event_key)
			curr_post.content = self.request.get('content')
			curr_post.author = user.name

			curr_post.put()

			self.redirect('/events?id=' + str(event.key().id()))
		else:
			self.redirect('/unauth')

class Profile(BaseHandler):
	def get(self):
		# user = users.get_current_user()
		# if user:
		# user_key = db.Key.from_path('User',user.email())
		# our_user = db.get(user_key)
		if self.user_info():
			user = self.get_user()
			template_values = {
			'user':user,
			'user_mail': user.email,
			# 'logout' : users.create_logout_url(self.request.host_url)
			}
			template = jinja_environment.get_template('profile.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect('/unauth')
		# else:
		# 	self.redirect(users.create_login_url(self.request.uri))

class Invite(BaseHandler):
	def post(self):
		# current_user_key = db.Key.from_path('User',users.get_current_user().email())
		# current_user = db.get(current_user_key)
		if self.user_info():
			current_user = self.get_user()

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
		else:
			self.redirect('/unauth')

class AddFriend(BaseHandler):
	def post(self):
		# current_user_key = db.Key.from_path('User',users.get_current_user().email())
		# current_user = db.get(current_user_key)
		if self.user_info():
			user = self.get_user()

			add_email = self.request.get('add_email')
			add_key = db.Key.from_path('User',add_email)
			added_user = db.get(add_key)

			added_user.received_request_list.append(user.email)
			added_user.put()

			user.sent_request_list.append(added_user.email)
			user.put()

			self.redirect('/home')
		else:
			self.redirect('/unauth')

class AcceptFriend(BaseHandler):
	def post(self):
		if self.user_info():
			user = self.get_user()

			if self.request.get('submitbutton') == 'Accept':
				add_email = self.request.get('add_email')
				add_key = db.Key.from_path('User',add_email)
				added_user = db.get(add_key)

				added_user.friends_list.append(user.email)
				added_user.sent_request_list.remove(user.email)
				added_user.put()

				user.friends_list.append(added_user.email)
				user.received_request_list.remove(added_user.email)
				user.put()
			elif self.request.get('submitbutton') == 'Reject':
				add_email = self.request.get('add_email')
				add_key = db.Key.from_path('User',add_email)
				added_user = db.get(add_key)

				added_user.sent_request_list.remove(user.email)
				added_user.put()

				user.received_request_list.remove(added_user.email)
				user.put()


			self.redirect('/home')
		else:
			self.redirect('/unauth')
class UserSearch(BaseHandler):
	def post(self):
		if self.user_info():
			search_item = self.request.get('search').rstrip()
			search_key = db.Key.from_path('User',search_item)
			target_user = db.get(search_key)

			# user_key = db.Key.from_path('User',users.get_current_user().email())
			# current_user = db.get(user_key)
			user = self.get_user()

			template_values = {
				'target_user': target_user,
				'target': search_item,
				'user_mail': user.email,
				'user': user,
				# 'logout': users.create_logout_url(self.request.host_url),
			}

			template = jinja_environment.get_template('display.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect('/unauth')


class Settings(BaseHandler):
	def get(self):
		if self.user_info():
			# user = users.get_current_user()
			# if user:
			user = self.get_user()
			template_values = {
			'user': user
			# 'logout' : users.create_logout_url(self.request.host_url)
			}
			template = jinja_environment.get_template('usersettings.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect('/unauth')
		# else:
		# 	self.redirect(users.create_login_url(self.request.uri))

class Messages(BaseHandler):
	def get(self):
		# user = users.get_current_user()
		# if user:
		if self.user_info():
			user = self.get_user()
			template_values = {
			'user': user
			# 'logout' : users.create_logout_url(self.request.host_url)
			}
			template = jinja_environment.get_template('usermsgs.html')
			self.response.out.write(template.render(template_values))
		else:
			self.redirect('/unauth')
		# else:
		# 	self.redirect(users.create_login_url(self.request.uri))

class Vote(BaseHandler):
	def post(self):
		if self.user_info():
			user = self.get_user()
			event_id = int(self.request.get('event_id'))
			event_key = db.Key.from_path('Event',event_id)
			option_id = int(self.request.get('option_id'))
			option_key = db.Key.from_path('Option',option_id,parent=event_key)
			option = db.get(option_key)

			if user.email not in option.voters:
				option.voters.append(user.email)
				option.votes += 1
				option.satisfied = (option.votes >= option.minimum)
				option.put()

			self.redirect('/events?id=' + str(event_id))
		else:
			self.redirect('/unauth')

class FbLoginHandler(BaseHandler):
	def get(self):
		args = dict(client_id=FACEBOOK_APP_ID, redirect_uri= server + "/fbauth",scope='email')
		self.redirect("https://graph.facebook.com/oauth/authorize?" + 
									urllib.urlencode(args))

class GLoginHandler(BaseHandler):
	def get(self):
		args = dict(client_id=GOOGLE_CLIENT_ID, redirect_uri= server + "/googleauth",
								scope="https://www.googleapis.com/auth/userinfo.email ", response_type="code")
		self.redirect("https://accounts.google.com/o/oauth2/auth?" + 
									urllib.urlencode(args))

class FbAuthHandler(BaseHandler):
	def get(self):
		args = dict(client_id=FACEBOOK_APP_ID, redirect_uri=server + "/fbauth",scope='email')
		args['client_secret'] = FACEBOOK_APP_SECRET
		args['code'] = self.request.get('code')
		#Confirming Identity
		response = cgi.parse_qs(urllib.urlopen(
    					"https://graph.facebook.com/oauth/access_token?" +
    					 urllib.urlencode(args)).read())
		#Generating Access Token
		access_token = response["access_token"][-1]

		#Validating Access Token (Use App Token)

		profile = json.load(urllib.urlopen(
							"https://graph.facebook.com/me?" + 
							urllib.urlencode(dict(access_token=access_token))))
		email = profile["email"]
		test_key = db.Key.from_path('User',email)
		test_user = db.get(test_key)
		# self.auth().unset_session()
		if test_user == None:
			newUser = User(key_name = email)
			newUser.email = email
			newUser.name = profile["name"]
			newUser.event_key_list = []
			newUser.auth_id = email
			newUser.fb_token = access_token
			newUser.put()
		else:
			test_user.fb_token = access_token
		# 	token = UserToken.create(newUser,'facebook',access_token)
		# else:
		# 	token = UserToken.create(test_user,'facebook',access_token)
		user = {'user_id':email, 'email':email}
		self.auth().set_session(user,User.create_auth_token(email))
		self.redirect('/')

class GAuthHandler(BaseHandler):
	def get(self):
		logging.warning('Beginning')
		args = dict(client_id=GOOGLE_CLIENT_ID, redirect_uri=server + "/googleauth")
		args['client_secret'] = GOOGLE_CLIENT_SECRET
		args['code'] = self.request.get('code') 
		args['grant_type'] = 'authorization_code'
		url = 'https://accounts.google.com/o/oauth2/token'
		data = urllib.urlencode(args)
		req = urllib.urlopen(url,data)
		response = req.read()
		# logging.warning(response)
		# logging.warning('Going to try for id token')
		id_token = client._extract_id_token(json.loads(response)["id_token"])
		email = id_token["email"]
		# access_token = crypt._urlsafe_b64decode(json.loads(response)["access_token"])
		# logging.warning(access_token)
		# logging.warning('Going to try for profile with' + access_token)
		# profile_response = urllib.urlopen(
		# 					"https://wwww.googleapis.com/oauth2/v1/userinfo?access_token=" + 
		# 					access_token).read()
		# logging.warning(profile_response)
		# profile = json.loads(profile_response)
		# logging.warning('Going to try for email')
		# email = profile["email"]
		test_key = db.Key.from_path('User',email)
		test_user = db.get(test_key)
		# self.auth().unset_session()
		if test_user == None:
			newUser = User(key_name = email)
			newUser.email = email
			newUser.name = email
			newUser.event_key_list = []
			newUser.auth_id = email
			newUser.g_token = id_token
			newUser.put()
		else:
			newUser.g_token = id_token
		user = {'user_id':email, 'email':email}
		self.auth().set_session(user,User.create_auth_token(email))
		self.redirect('/')

# Static Pages

class Unauth(BaseHandler):
	def get(self):
		template = jinja_environment.get_template('unauth.html')
		self.response.out.write(template.render())

class FrontPage(BaseHandler):
    def get(self):
    	if self.user_info():
    		self.redirect('/home')
    	else:
	    	template = jinja_environment.get_template('front.html')
	    	src = self.request.get('src')
	    	if src == 'fail_login':
	    		template_values = {'fail_login':True,'fail_signup':False}
	    	elif src == 'fail_signup':
	    		template_values = {'fail_login':False,'fail_signup':True}
	    	else:
	    		template_values = {'fail_login':False,'fail_signup':False}
	    	self.response.out.write(template.render(template_values))

class About(BaseHandler):
    def get(self):
        template = jinja_environment.get_template('about.html')
        self.response.out.write(template.render())

class Contact(BaseHandler):
    def get(self):
        template = jinja_environment.get_template('contact.html')
        self.response.out.write(template.render())

class Help(BaseHandler):
	def get(self):
		template = jinja_environment.get_template('help.html')
		self.response.out.write(template.render())

config = {
	'webapp2_extras.auth': {
		'user_model' : 'demeetr.User',
		'user_attributes': ['email']
	},
	'webapp2_extras.sessions': {
		'secret_key': 'DemeetrSecretKey'
	}
}

app = webapp2.WSGIApplication([('/home',HomePage),
<<<<<<< HEAD
								('/signup',Signup),
								('/login',Login),
								('/logout',Logout),
								('/messages',Messages),
								('/settings',Settings),
								('/profile',Profile),
								('/events',Events),
								('/search',UserSearch),
								('/invite',Invite),
								('/addoption',AddOption),
								('/addavailability',AddAvailability),
								('/addfriend',AddFriend),
								('/eventvote',Vote),
								('/unauth',Unauth),
								('/', FrontPage),
							    ('/about', About),
							   	('/contact',Contact),
							    ('/help',Help),
							    ('/fblogin',FbLoginHandler),
							    ('/fbauth',FbAuthHandler),
								('/addevent',AddEvent)],
								debug = True, config=config)
=======
															('/signup',Signup),
															('/login',Login),
															('/logout',Logout),
															('/messages',Messages),
															('/settings',Settings),
															('/profile',Profile),
															('/events',Events),
															('/search',UserSearch),
															('/invite',Invite),
															('/addoption',AddOption),
															('/addpost',AddPost),
															('/addfriend',AddFriend),
															('/eventvote',Vote),
															('/unauth',Unauth),
															('/', FrontPage),
							    						('/about', About),
							   							('/contact',Contact),
							    						('/help',Help),
							    						('/accept',AcceptFriend),
							    						('/fblogin',FbLoginHandler),
							    						('/fbauth',FbAuthHandler),
							    						('/googlelogin',GLoginHandler),
							    						('/googleauth',GAuthHandler),
															('/addevent',AddEvent)],
															debug = True, config=config)
>>>>>>> b45bb6360f7e3cfeae24401a7039ef970d0268d9
