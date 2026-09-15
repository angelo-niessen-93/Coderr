# Coderr Backend

Coderr is a backend-only Django REST Framework project for a freelancer marketplace. It provides authentication, profile, offer, order, review, and platform statistics APIs under `/api/`.

## Prerequisites

- Python 3.14 or a compatible Python 3 version for the pinned dependencies
- pip
- Git

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Configuration

The project uses SQLite for local development by default. Configuration is loaded from process environment variables and, for local development, from `.env`.

Create local configuration from the example file:

```bash
copy .env.example .env
```

`SECRET_KEY` is required. Replace the placeholder in `.env` with a secure local value and never commit `.env`. You can generate a safe Django key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Optional environment variables:

- `DJANGO_DEBUG`: set to `False` outside local development
- `DJANGO_ALLOWED_HOSTS`: comma-separated allowed hosts

Local CORS origins are configured for common frontend development ports: `3000` and `5173` on `localhost` and `127.0.0.1`.

## Database

Apply migrations:

```bash
python manage.py migrate
```

Check for pending model migrations:

```bash
python manage.py makemigrations --check --dry-run
```

## Run The Server

Start the local development server:

```bash
python manage.py runserver
```

The API is available below:

```text
http://127.0.0.1:8000/api/
```

## Tests

Run Django checks and tests:

```bash
python manage.py check
python manage.py test
```

Run coverage:

```bash
python -m coverage run manage.py test
python -m coverage report
```

## Project Structure

The Django project is named `core`. Functional apps are split by domain:

- `auth_app`
- `profile_app`
- `offers_app`
- `orders_app`
- `reviews_app`

API code lives in each app's `api/` package where applicable. The cross-app base information endpoint lives in `core/api/`.

## API Routing

All public API routes are mounted below `/api/` from `core/urls.py`. App-specific route definitions live in each app's `api/urls.py`.

Media files are served from `MEDIA_ROOT` during local development when `DEBUG=True`.
