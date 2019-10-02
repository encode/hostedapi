from starlette.config import Config

config = Config()

DEBUG = config("DEBUG", cast=bool, default=False)
SENTRY_DSN = config("SENTRY_DSN", cast=str, default="")
