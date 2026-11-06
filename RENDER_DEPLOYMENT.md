# Deploying to Render

This repository includes a Render Blueprint at `render.yaml`. It creates a
Docker web service, a persistent PostgreSQL database, and a persistent disk for
uploaded files. These are paid Render resources; review the current prices in
Render before confirming the Blueprint.

## Deploy

1. Push this repository, including `render.yaml`, to GitHub.
2. In Render, choose **New → Blueprint**, connect this repository, and apply
   the Blueprint.
3. Wait for the first deploy to finish. The container runs tenant migrations
   before starting Gunicorn.
4. In the web service's **Shell**, run `python manage.py create_lan_shop`.
   Enter the shop name, schema ID, and administrator details when prompted.
   The command uses `RENDER_EXTERNAL_HOSTNAME` to register the deployed URL
   for the first shop.
5. Open the Render service URL and sign in at `/login/`.

The database starts empty; local SQLite records are not imported. The media
disk preserves uploaded images and documents across service deploys.

The tenant registration page currently creates `.localhost` domains and is
intended for local development. This Blueprint sets up one shop on the Render
service hostname; custom-domain or subdomain routing for additional shops
needs separate domain/DNS configuration.
