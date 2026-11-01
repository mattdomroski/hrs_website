import os

from dotenv import find_dotenv, dotenv_values

STAFF_PORTAL_URL = 'localhost:5000'

try:
    dotenv_path = find_dotenv(raise_error_if_not_found=True)
except OSError:
    raise FileNotFoundError('No .env file found')

env = dotenv_values()

def get_env_value(key):
    try:
        return env[key]
    except KeyError:
        raise KeyError(f'Undefined environment variable "{key}". Define it in {dotenv_path}')

#Load all environment variables here so any missing variables are caught at startup.
DB_HOST = get_env_value('DB_HOST')
DB_USER = get_env_value('DB_USER')
DB_PASSWORD = get_env_value('DB_PASSWORD')
DB_NAME = get_env_value('DB_NAME')
DB_PORT = int(get_env_value('DB_PORT'))