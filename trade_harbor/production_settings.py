from trade_harbor import env

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.get('DEBUG', default=False)
