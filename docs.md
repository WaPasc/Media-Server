
## Database Migrations
```bash
python -m alembic revision --autogenerate -m "Initial migration"
python -m alembic upgrade head
```

## Python
This command will install the package in editable mode, allowing you to make changes to the code and have them reflected without needing to reinstall the package.
```bash
pip install -e .
```