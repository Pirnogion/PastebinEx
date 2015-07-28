from HTMLParser import HTMLParser

import urllib
from urllib2 import Request, build_opener, HTTPCookieProcessor, HTTPHandler
import urllib2
import cookielib
import json

import sublime, sublime_plugin

def plugin_loaded():
	sublime.message_dialog("LOADED")

#------------------------------------------------------------
#Pastebin
#------------------------------------------------------------
class ERROR():
	ERROR_CODES_LOGIN_API = {
		'Bad API request, use POST request, not GET'							:1,
		'Bad API request, invalid api_dev_key'									:2,
		'Bad API request, invalid login'										:3,
		'Bad API request, account not active'									:4,
		'Bad API request, invalid POST parameters'								:5,
		'Bad API request, too many logins in 5 minutes. Blocked for 5 minutes.'	:6
	}

	ERROR_CODES_CREATE_PASTE = {
		'Bad API request, invalid api_option'											:1,
		'Bad API request, invalid api_dev_key'											:2,
		'Bad API request, IP blocked'													:3,
		'Bad API request, maximum number of 25 unlisted pastes for your free account'	:4,
		'Bad API request, maximum number of 10 private pastes for your free account'	:5,
		'Bad API request, api_paste_code was empty'										:6,
		'Bad API request, maximum paste file size exceeded'								:7,
		'Bad API request, invalid api_expire_date'										:8,
		'Bad API request, invalid api_paste_private'									:9,
		'Bad API request, invalid api_paste_format'										:10
	}

	ERROR_CODES_DELETE_PASTE = {
		'Bad API request, invalid api_option'					:1,
		'Bad API request, invalid api_dev_key'					:2,
		'Bad API request, invalid api_user_key'					:3,
		'Bad API request, invalid permission to remove paste'	:4
	}

	ERROR_CODES_LOGIN = {
		'ERR': 1
	}

	ERROR_CODES_MODIFY_PASTE = {
		'ERR' :1
	}

	ERROR_CODES_GET_PASTE = {
		'ERR' :1
	}

	UNEXPECTED_ERROR = 0

class PastebinShell():
	#User info
	post_key = None

	#Login with use pastebin API
	dev_key = 'e98db6da803203282d172156bc46137c'

	#Pastebin urls
	pastebin_api = "http://pastebin.com/api/api_post.php"
	pastebin_api_login = "http://pastebin.com/api/api_login.php"

	pastebin_login = "http://pastebin.com/login.php"
	pastebin_post = "http://pastebin.com/post.php"
	pastebin_edit = "http://pastebin.com/edit.php"
	pastebin_get = "http://pastebin.com/raw.php"

	def login(self, username, password):
		cookiejar = cookielib.CookieJar()
		opener = build_opener(HTTPCookieProcessor(cookiejar), HTTPHandler())

		login_value = {'submit_hidden':'submit_hidden', 'user_name':username, 'user_password':password, 'submit':'Login'}
		try:
			login_data = urllib.urlencode(login_value)
			login_request = Request(self.pastebin_login, login_data)
			login_response = opener.open(login_request)
		except Exception, e:
			return ERROR.UNEXPECTED_ERROR, e
		else:
			#Get session cookie
			session_cookie = ''
			for cookie in cookiejar:
				session_cookie = session_cookie + cookie.name + '=' + cookie.value + '; '

			return None, session_cookie
		finally:
			login_response.close()

	def modify_paste(self, paste_id, header, text, cookie):
		#Send request for get post key
		try:
			pk_req = urllib2.Request(self.pastebin_edit + "?i=" + paste_id)
			pk_req.add_header('Cookie', cookie)
			pk_response = urllib2.urlopen(pk_req)
			pk_html = pk_response.read()
		except Exception, e:
			return ERROR.UNEXPECTED_ERROR, e
		else:
			#Parse HTML response and get postkey
			parser = getPostKey()
			parser.feed(pk_html)
			self.post_key = parser.pk

			#Modify paste
			edit_value = {'submit_hidden':'submit_hidden', 'item_key':paste_id, 'post_key':self.post_key, 'paste_code':text, 'paste_format':'30', 'paste_expire_date':'DNC', 'paste_private':'0', 'paste_name':header, 'submit':'Submit'}
			try:
				edit_data = urllib.urlencode(edit_value).encode('utf8')
				edit_req = urllib2.Request(self.pastebin_edit, edit_data)
				edit_req.add_header('Cookie', cookie)
				edit_response = urllib2.urlopen(edit_req)
			except Exception, e:
				return ERROR.UNEXPECTED_ERROR, e
			else:
				return None, True
			finally:
				edit_response.close()
		finally:
			pk_response.close()

	def login_api(self, username, password):
		#Get userkey
		login_api_value = {'api_dev_key':self.dev_key, 'api_user_name':username, 'api_user_password':password}
		try:
			login_api_data = urllib.urlencode(login_api_value)
			login_api_req = urllib2.Request(self.pastebin_api_login, login_api_data)
			login_api_response = urllib2.urlopen(login_api_req)
			login_html = login_api_response.read();
		except Exception, e:
			return ERROR.UNEXPECTED_ERROR, e
		else:
			return ERROR.ERROR_CODES_LOGIN_API.get(login_html, None), login_html
		finally:
			login_api_response.close()

	def create_paste(self, header, text, user_key):
		cpaste_value = {'api_option':'paste', 'api_dev_key':self.dev_key, 'api_user_key':user_key, 'api_paste_private':'0', 'api_paste_format':'lua', 'api_paste_name':header, 'api_paste_code':text}
		try:
			cpaste_data = urllib.urlencode(cpaste_value)
			cpaste_req = urllib2.Request(self.pastebin_api, cpaste_data)
			cpaste_response = urllib2.urlopen(cpaste_req)
			cpaste_html = cpaste_response.read()
		except Exception, e:
			return ERROR.UNEXPECTED_ERROR, e
		else:
			return ERROR.ERROR_CODES_CREATE_PASTE.get(cpaste_html, None), cpaste_html
		finally:
			cpaste_response.close()

	def delete_paste(self, paste_id, user_key):
		dpaste_value = {'api_option':'delete', 'api_dev_key':self.dev_key, 'api_user_key':user_key, 'api_paste_key':paste_id}
		try:
			dpaste_data = urllib.urlencode(dpaste_value)
			dpaste_req = urllib2.Request(self.pastebin_api, dpaste_data)
			dpaste_response = urllib2.urlopen(dpaste_req)
			dpaste_html = dpaste_response.read()
		except Exception, e:
			return ERROR.UNEXPECTED_ERROR, e
		else:
			return ERROR.ERROR_CODES_DELETE_PASTE.get(dpaste_html, None), dpaste_html
		finally:
			dpaste_response.close()

	def get_paste(self, paste_id):
		try:
			gpaste_req = urllib2.Request(self.pastebin_get + "?i=" + paste_id)
			gpaste_response = urllib2.urlopen(gpaste_req)
			gpaste_html = gpaste_response.read()
		except Exception, e:
			return ERROR.UNEXPECTED_ERROR, e
		else:
			return ERROR.ERROR_CODES_GET_PASTE.get(gpaste_html, None), gpaste_html
		finally:
			gpaste_response.close()

	#def list():
		#nop
#------------------------------------------------------------
class getPostKey(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.isPostKey = False
		self.pk = None
	def handle_starttag(self, tag, attrs):
		if tag == 'input':
			for name, value in attrs:
				if value == 'post_key':
					self.isPostKey = True
					continue
				if name == 'value' and self.isPostKey == True:
					self.isPostKey = False
					self.pk = value
					break

#------------------------------------------------------------
#Utils
#------------------------------------------------------------
class VisibleManager():
	LoginVisible 		= True
	LogoutVisible 		= False
	CreatePasteVisible 	= False
	ModifyPasteVisible 	= False
	DeletePasteVisible 	= False

	GetPasteVisible 	= True

	def ToggleVisibleLoginLogout(self):
		visibleManager.LoginVisible = not visibleManager.LoginVisible
		visibleManager.LogoutVisible = not visibleManager.LogoutVisible

		visibleManager.CreatePasteVisible = not visibleManager.CreatePasteVisible
		visibleManager.ModifyPasteVisible = not visibleManager.ModifyPasteVisible
		visibleManager.DeletePasteVisible = not visibleManager.DeletePasteVisible
		#visibleManager.GetPasteVisible = not visibleManager.GetPasteVisible

#------------------------------------------------------------
#EventHandler
#------------------------------------------------------------
#class EventHandlerCommand(sublime_plugin.EventListener):
#	def 

#------------------------------------------------------------
#Commands handlers
#------------------------------------------------------------
pastebin = PastebinShell()
session_settings_base = "Session.sublime-settings"
visibleManager = VisibleManager()
prev_pasteid = ''

class LoginCommand(sublime_plugin.TextCommand):
	username = None
	password = None

	def run(self, edit):
		session_settings = sublime.load_settings(session_settings_base)

		if not session_settings.get('loggedin', False):
			self.view.window().show_input_panel('Input your username: ', '', self.InputUsernameHandler, None, None)
		else:
			visibleManager.ToggleVisibleLoginLogout()

	def InputUsernameHandler(self, onEvent):
		if len(onEvent) > 1:
			self.username = onEvent
			self.view.window().show_input_panel('Input your password: ', '', self.InputPasswordHandler, None, None)
		else:
			sublime.error_message("Please, enter minimum 1 symbol!")

	def InputPasswordHandler(self, onEvent):
		if len(onEvent) > 1:
			self.password = onEvent
			self.Login()
		else:
			sublime.error_message("Please, enter minimum 1 symbol!")

	def Login(self):
		session_settings = sublime.load_settings(session_settings_base)

		errcode, response = pastebin.login(self.username, self.password)
		if errcode == ERROR.UNEXPECTED_ERROR or not(errcode is None):
			sublime.error_message("Unexpected error.")
		else:
			cookie = response
			session_settings.set('cookie', cookie)
			session_settings.set('loggedin_browser', True)

		errcode, response = pastebin.login_api(self.username, self.password)
		if errcode == 6:
			sublime.error_message("Spam protection: login in 5 minutes.")
		elif errcode == 3:
			sublime.error_message("Invalid username or password.")
		elif errcode == ERROR.UNEXPECTED_ERROR or not(errcode is None):
			sublime.error_message("Unexpected error.")
		else:
			user_key = response
			session_settings.set('user_key', user_key)
			session_settings.set('loggedin_api', True)

		if session_settings.get('loggedin_browser', False) and session_settings.get('loggedin_api', False):
			session_settings.set('loggedin', True)
			visibleManager.ToggleVisibleLoginLogout()

			sublime.message_dialog('Logged in!')
		else:
			session_settings.set('loggedin_browser', False)
			session_settings.set('loggedin_api', False)
			session_settings.set('loggedin', False)

			sublime.error_message('Login failed!')

		sublime.save_settings(session_settings_base)

	def is_visible(self):
		return visibleManager.LoginVisible

class LogoutCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		session_settings = sublime.load_settings(session_settings_base)
		session_settings.set('cookie', None)
		session_settings.set('user_key', None)
		session_settings.set('loggedin', False)
		sublime.save_settings(session_settings_base)

		visibleManager.ToggleVisibleLoginLogout()

	def is_visible(self):
		return visibleManager.LogoutVisible

class CreatePasteCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		userkey = sublime.load_settings(session_settings_base).get('user_key', None)
		if userkey is None:
			sublime.error_message("Wrong session! Relogin, please.")
		else:
			paste = self.view.substr(sublime.Region(0, self.view.size()))

			errcode, response = pastebin.create_paste("New Paste!", paste, userkey)
			if errcode == 7:
				sublime.error_message("maximum paste file size exceeded")
			elif errcode == 3:
				sublime.error_message("Your IP addres blocked by Pastebin.com, sorry.")
			elif errcode == 4:
				sublime.error_message("Maximum number of 25 unlisted pastes for your free account.")
			elif errcode == 5:
				sublime.error_message("Maximum number of 10 private pastes for your free account.")
			elif errcode == ERROR.UNEXPECTED_ERROR or not(errcode is None):
				sublime.error_message("Unexpected error.")
			else:
				sublime.message_dialog("Paste " + response + " successfully created.")

	def is_visible(self):
		return visibleManager.CreatePasteVisible

class ModifyPasteCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.edit = edit
		self.view.window().show_input_panel('Input pasteid: ', prev_pasteid, self.InputPasteIdHandler, None, None)

	def InputPasteIdHandler(self, onEvent):
		cookie = sublime.load_settings(session_settings_base).get('cookie', None)
		if cookie is None:
			sublime.error_message("Wrong session! Relogin, please.")
		else:
			if len(onEvent) > 1:
				prev_pasteid = onEvent
				paste = self.view.substr(sublime.Region(0, self.view.size()))
				errcode, response = pastebin.modify_paste(prev_pasteid, "New Handler! 2000", paste, cookie)

				if errcode == ERROR.UNEXPECTED_ERROR:
					sublime.error_message("Unexpected error.")
				else:
					sublime.message_dialog("Paste " + prev_pasteid + " successfuly modifed!")

			else:
				sublime.error_message("Please, enter minimum 1 symbol!")

	def is_visible(self):
		return visibleManager.ModifyPasteVisible

class DeletePasteCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.edit = edit
		self.view.window().show_input_panel('Input pasteid: ', prev_pasteid, self.InputPasteIdHandler, None, None)

	def InputPasteIdHandler(self, onEvent):
		userkey = sublime.load_settings(session_settings_base).get('user_key', None)
		if userkey is None:
			sublime.error_message("Wrong session! Relogin, please.")
		else:
			if len(onEvent) > 1:
				prev_pasteid = onEvent
				errcode, response = pastebin.delete_paste(prev_pasteid, userkey)
				print errcode
				print response
				if errcode == 4:
					sublime.error_message("Your don't remove this paste!")
				elif errcode == ERROR.UNEXPECTED_ERROR or not(errcode is None):
					sublime.error_message("Unexpected error.")
				else:
					paste = response.decode('utf8')
					sublime.message_dialog("Paste " + prev_pasteid + " successfuly deleted!")
			else:
				sublime.error_message("Please, enter minimum 1 symbol!")

	def is_visible(self):
		return visibleManager.DeletePasteVisible

class GetPasteCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.edit = edit
		self.view.window().show_input_panel('Input pasteid: ', prev_pasteid, self.InputPasteIdHandler, None, None)

	def InputPasteIdHandler(self, onEvent):
		if len(onEvent) > 1:
			prev_pasteid = onEvent
			errcode, response = pastebin.get_paste(prev_pasteid)
			if errcode == ERROR.UNEXPECTED_ERROR or not(errcode is None):
				sublime.error_message("Unexpected error.")
			else:
				paste = response.decode('utf8')
				self.view.insert( self.edit, 0, paste )
		else:
			sublime.error_message("Please, enter minimum 1 symbol!")

	def is_visible(self):
		return visibleManager.GetPasteVisible

#------------------------------------------------------------
#Scrap
#------------------------------------------------------------
#self.content = self.view.substr(sublime.Region(0, self.view.size()))
#self.paste_id = self.view.substr( self.view.line(0) )[1:]
