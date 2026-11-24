from dotenv import load_dotenv
import os

load_dotenv()

#Load all environment variables here so any missing variables are caught at startup.
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_PORT = int(os.getenv('DB_PORT'))
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
STAFF_PORTAL_URL = os.getenv('STAFF_PORTAL_URL')
