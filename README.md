# Coderr Backend

Coderr is a backend-only Django REST Framework project for a freelancer marketplace.

## Project Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run Django checks:

```bash
python manage.py check
```

Run database migrations when models are added:

```bash
python manage.py migrate
```

Start the local development server:

```bash
python manage.py runserver
```

## Structure

The Django project is named `core`. Domain concerns are split into dedicated apps:

- `auth_app`
- `profiles_app`
- `offers_app`
- `orders_app`
- `reviews_app`

Each app that exposes API endpoints contains an `api/` package for serializers, views, URLs, and app-specific permissions where needed.

## API Routing

All API routes are mounted below `/api/` from `core/urls.py`. App-specific route definitions live in each app's `api/urls.py`.

## Local Development

CORS is configured for common local frontend development origins:

- `http://localhost:3000`
- `http://localhost:5173`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:5173`

Media files are served during local development from `MEDIA_ROOT`.
