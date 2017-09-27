from google.cloud import storage
import sys

def upload_file(file_stream, filename):
    client = storage.Client()
    bucket = client.bucket('labo-cdn.appspot.com')
    blob = bucket.blob(filename)

    blob.upload_from_file(file_stream)
    blob.make_public()
    url = blob.public_url

    if url:
        url = url.decode('utf-8')

    return url

if len(sys.argv) is 2:
    with open(sys.argv[1], 'rb') as f:
        print(upload_file(f, sys.argv[1]))
