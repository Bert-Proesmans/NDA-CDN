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

import webapp2
import mimetypes
import re
import cloudstorage
from urlparse import urlparse
#import google.cloud

def getContentType(filename):
	if filename.lower().endswith('.css'):
		return "text/css"
	return mimetypes.MimeTypes().guess_type(filename)[0]

# https://stackoverflow.com/questions/8567171/how-do-i-remove-a-query-from-a-url
def filterURL(filename):
	o = urlparse(filename)
	url_without_query_string = o.path[1:]
	return url_without_query_string

class ContentServerGAE(webapp2.RequestHandler):
	BUCKET_NAME = "labo-cdn.appspot.com"

	def get(self, filename):
		# We add a 'valid' domain to be able to use this library, kind of hackish but it works
		filename = filterURL("http://example.com/" + filename)
		filename = "/" + self.BUCKET_NAME + "/" + filename
		self.__hasExtenstionPattern = re.compile("^.+\.([a-zA-Z0-9])*$")
		content = ""
		contentType = getContentType(filename)

		if not self.__hasExtenstionPattern.match(filename):
			filenameIndexed = filename[:]
			if not filenameIndexed.endswith("/"):
				filenameIndexed = filenameIndexed + "/"

			filenameIndexed = filenameIndexed + "index.html"
			try:
				with cloudstorage.open(filenameIndexed) as gcs_file:
					content = content + gcs_file.read()

				contentType = getContentType(filenameIndexed)
				self.sendResponse(content, contentType)
				return 

			except cloudstorage.NotFoundError:
				pass
		
		try:
			with cloudstorage.open(filename) as gcs_file:
				content = content + gcs_file.read()

			self.sendResponse(content, contentType)

		except cloudstorage.NotFoundError:
			self.abort(404)
			pass

	def sendResponse(self, output, contentType):
		self.response.headers['Content-Type'] = contentType
		if contentType is "application/pdf":
			self.response.headers['Content-Disposition'] = "inline"
		
		self.response.write(output)

"""
class ContentServerGC(webapp2.RequestHandler):
	BUCKET_NAME = "labo-cdn.appspot.com"

	def get(self, filename):
		self.__storageClient = google.cloud.storage.Client.from_service_account_json('content-server-auth.json')
		self.__storageBucket = self.__storageClient.bucket(self.BUCKET_NAME)
		self.__hasExtenstionPattern = re.compile("^.+\.([a-zA-Z0-9])*$")

		content = ""

		contentType = getContentType(filename)[0]
		blob = self.__storageBucket.blob(filename)

		if not self.__hasExtenstionPattern.match(filename):
			if not filename.endswith("/"):
				filename = filename + "/"

			filename = filename + "index.html"
			indexedBlob = self.__storageBucket.blob(filename)

			try:
				content = indexedBlob.download_as_string()
				contentType = getContentType(filename)[0]
				self.sendResponse(content, contentType)

			except google.cloud.exceptions.NotFound:
				pass
		
		try:
			content = blob.download_as_string()
			self.sendResponse(content, contentType)

		except google.cloud.exceptions.NotFound:
			self.sendResponse("Not found", "text/plain")
			pass

	def sendResponse(output, contentType):
		self.response.headers['Content-Type'] = contentType
		if contentType is "application/pdf":
			self.response.headers['Content-Disposition'] = "inline"
		
		self.response.write(output)
"""

app = webapp2.WSGIApplication([
	webapp2.Route(r'/<:.*>', handler=ContentServerGAE),
], debug=True)
