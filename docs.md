
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


## Docker commands
This command builds a Docker image from the current directory (.), using the Dockerfile located there. The -t media-server-backend flag assigns a name (tag) to the image.
```bash
docker build -t media-server-backend . 
```

This command starts a container named ms-backend from the previously built image. It maps port 8000, loads environment variables from .env, and mounts local directories into the container to persist media files and application data.
```bash
docker run --name ms-backend \                                                                                                         
  -p 8000:8000 \                                                                                               
  --env-file .env \                   
  -v /.../Videos/media:/media \                                                                      
  -v $(pwd)/app_data:/app/data \                                                                    
  media-server-backend   
```