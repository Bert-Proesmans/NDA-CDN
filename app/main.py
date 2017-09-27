# Copyright 2016 Google Inc.
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


import urllib2
import webapp2
import mimetypes

def getContentType(filename, url):
	contentType = mimetypes.MimeTypes().guess_type(filename)
	return contentType

class MainHandler(webapp2.RequestHandler):
	def get(self, filename):
		# Get file from CDN
		cdn = urllib2.urlopen("https://storage.googleapis.com/labo-cdn.appspot.com/" + filename)
		contentType = getContentType(filename, cdn)[0]

		self.response.headers['Content-Type'] = contentType
		if contentType is "application/pdf":
			self.response.headers['Content-Disposition'] = "inline"
		
		self.response.write(cdn.read())

class TestHandler(webapp2.RequestHandler):
	def get(self, filename):
		cdn = urllib2.urlopen("https://storage.googleapis.com/labo-cdn.appspot.com/" + filename)
		contentType = getContentType(filename, cdn)[0]

		self.response.headers['Content-Type'] = "text/plain"
		self.response.write("You've entered: " + filename + "<br />" + contentType)

app = webapp2.WSGIApplication([
	webapp2.Route(r'/load/<:.*>', handler=MainHandler),
	webapp2.Route(r'/test/<:.*>', handler=TestHandler)
], debug=True)
