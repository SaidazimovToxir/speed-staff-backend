# #!/bin/bash
# set -e

# # Wait for postgres to be ready (optional but recommended in prod)
# # You could add a small python script or wait-for-it here if needed.
# # For now, we will just wait a few seconds assuming compose brings db up first
# sleep 5

# echo "Applying database migrations..."
# alembic upgrade head

# echo "Starting Uvicorn..."
# # In production it's much better to run via Gunicorn with Uvicorn workers, but for a 
# # direct setup we can run Uvicorn.
# exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'

# #!/bin/bash
# # set -e

# # echo "Waiting for PostgreSQL..."
# # until pg_isready -h db -p 5432 -U ${POSTGRES_USER:-postgres}; do
# #   echo "PostgreSQL is unavailable - retrying in 2s..."
# #   sleep 2
# # done

# # echo "PostgreSQL is ready!"

# # echo "Applying database migrations..."
# # alembic upgrade head

# # echo "Starting Uvicorn server..."
# # exec uvicorn app.main:app \
# #   --host 0.0.0.0 \
# #   --port 8000 \
# #   --proxy-headers \
# #   --forwarded-allow-ips='*'

#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h db -p 5432 -U ${POSTGRES_USER:-postgres}; do
  echo "PostgreSQL is unavailable - retrying in 2s..."
  sleep 2
done

echo "PostgreSQL is ready!"

echo "Applying database migrations..."
alembic upgrade head

echo "Starting Uvicorn server..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips='*'