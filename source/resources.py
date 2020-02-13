from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from source import settings
from source.broadcast import Broadcast
import databases
import httpx


templates = Jinja2Templates(directory="templates")
statics = StaticFiles(directory="statics")


if settings.TESTING:
    database = databases.Database(settings.TEST_DATABASE_URL, force_rollback=True)
else:  # pragma: nocover
    database = databases.Database(settings.DATABASE_URL)

broadcast = Broadcast(settings.REDIS_URL)


def url_for(*args, **kwargs):
    from source.app import app

    return app.url_path_for(*args, **kwargs)
