#!/bin/bash
# entrypoint.sh

# Wait for PostgreSQL to be available
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

# Initialize the database
python app.py db init
python app.py db migrate
python app.py db upgrade

# Run the application
exec "$@"

