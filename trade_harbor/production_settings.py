import sentry_sdk

from trade_harbor import env

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.get('DEBUG', default=False)


sentry_sdk.init(
    dsn=env.get('SENTRY_DSN'),
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = ["*"]
