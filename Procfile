release: python manage.py migrate
web: python manage.py collectstatic --noinput --clear; daphne dubito.asgi:application --port $PORT --bind 0.0.0.0 -v2
worker: python manage.py runworker --settings=dubito.settings -v2
