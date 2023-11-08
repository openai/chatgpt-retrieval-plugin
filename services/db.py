import os
import firebase_admin
from firebase_admin import db
from dotenv import load_dotenv

load_dotenv()

cred_obj = firebase_admin.credentials.Certificate('mekonggpt-firebase-adminsdk-tl6je-751134b214.json')
default_app = firebase_admin.initialize_app(cred_obj, {
	'databaseURL': os.getenv('FIREBASE_URL')
	})

ref = db.reference('/')

def get_refresh_token():
	return ref.get()['REFRESH_TOKEN']

def set_refresh_token(token):
	ref.update({'REFRESH_TOKEN': token})

if __name__ == '__main__':
	set_refresh_token('pM-FQ60_Lo_9OOXZOJ9HBy1YZ6blArfhd1_QPqqAH6A58yzWQN9uOguaf5jdTYv4YtoeMYii0ahgF8984M913BnnoX5SNrOSj63x8tarVmEH6_WoQ3b08Qattsnd54XJbYhvT54aRMkVRi9yKKj8SvP_oK1l8M9peWcXVdG7EcMuEA9IPcWbJ9ew_mvw57qaaJdd9tyMFIUGFQO0GW8aEBHMhZTjIHSwWboh82W8FpA33QO1I1vv9QWzm0L4F5GUiXZj4tWvTWsf3CW8O2TM5Oy7q0Kc2sq6y5JtCbz4BtQg5fj9OpmC19atga9d5Wu7gJIjAa4t5M_XEB1Y8Gm8KVeftr0sA5z4uJh1GH1kPW3yUCKv9InZ0UKCnH55D7q1c6QYE3109WpGJ_59c6VkTM4cKoK')