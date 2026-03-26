
## Database Migrations
```bash
python -m alembic revision --autogenerate -m "Initial migration"
python -m alembic upgrade head
```