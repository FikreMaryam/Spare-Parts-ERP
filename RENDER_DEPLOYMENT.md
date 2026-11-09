# Deploying to Render

This repository includes a Render Blueprint at `render.yaml`. It creates a
Docker web service, a persistent PostgreSQL database, and a persistent disk for
uploaded files. These are paid Render resources; review the current prices in
Render before confirming the Blueprint.

## Clean deployment checklist

1. Push this repository, including `render.yaml`, to GitHub.
2. In Render, choose **New → Blueprint**, connect this repository, and apply
   the Blueprint.
3. Confirm that the web service runtime is set to Docker and the environment
   variables are created by the Blueprint (`DEBUG`, `USE_SQLITE`,
   `DJANGO_SECRET_KEY`, `DATABASE_URL`, `MEDIA_ROOT`).
4. Wait for the first deploy to finish. The container runs tenant migrations
   before starting Gunicorn.
5. In the web service's **Shell**, run `python manage.py create_lan_shop`.
   Enter the shop name, schema ID, and administrator details when prompted.
   The command uses `RENDER_EXTERNAL_HOSTNAME` to register the deployed URL
   for the first shop.
6. Open the Render service URL and sign in at `/login/`.

## Production settings notes

- The app defaults to SQLite when `USE_SQLITE=True`.
- For Render, keep `USE_SQLITE=False` and supply `DATABASE_URL` or the
  `POSTGRES_*` variables so Django connects to the managed PostgreSQL instance.
- The database starts empty; local SQLite records are not imported.
- The media disk preserves uploaded images and documents across service deploys.

The tenant registration page currently creates `.localhost` domains and is
intended for local development. This Blueprint sets up one shop on the Render
service hostname; custom-domain or subdomain routing for additional shops
needs separate domain/DNS configuration.
