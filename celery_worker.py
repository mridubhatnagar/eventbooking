from app import create_app
from app.extensions import celery

# create_app() imports every domain's controller -> service -> tasks chain,
# which registers all Celery tasks onto the shared `celery` instance.
create_app()

if __name__ == "__main__":
    celery.start()
