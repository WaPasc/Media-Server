from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.schemas.scanner import ScanDirectoryCreate, ScanDirectoryResponse
from app.services import scanner_service

router = APIRouter(prefix='/api/scanner', tags=['scanner'])


@router.get('/directories', response_model=list[ScanDirectoryResponse])
async def get_directories(db: AsyncSession = Depends(get_db)):
    """List all directories currently being monitored."""
    return await scanner_service.get_all_directories(db)


@router.delete('/directories/{directory_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_directory(directory_id: int, db: AsyncSession = Depends(get_db)):
    """Remove a directory from being monitored."""
    success = await scanner_service.delete_scan_directory(db, directory_id)

    if not success:
        raise HTTPException(status_code=404, detail='Directory not found')


@router.post('/directories', response_model=ScanDirectoryResponse)
async def add_directory(
    directory: ScanDirectoryCreate, db: AsyncSession = Depends(get_db)
):
    """Add a new directory to monitor."""
    if directory.media_type not in ['movies', 'shows']:
        raise HTTPException(
            status_code=400, detail="media_type must be 'movies' or 'shows'"
        )

    return await scanner_service.add_scan_directory(
        db, directory.path, directory.media_type
    )


@router.post('/scan')
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger a full library scan in the background."""
    background_tasks.add_task(scanner_service.run_full_scan)
    return {
        'message': 'Scan started in the background. Check server logs for progress.'
    }
