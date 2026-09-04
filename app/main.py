from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, Header, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .db import init_db, get_db
from .config import get_settings
from .schemas import ImportRequest, SyncRequest
from .service import BridgeService
from .snapshot import RallySnapshotStore, SnapshotError

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title='Rally ↔ GitLab Bridge', version='0.2.0', lifespan=lifespan)
templates = Jinja2Templates(directory='app/templates')

@app.get('/health')
def health(): return {'status':'ok', 'version':'0.2.0'}

@app.get('/', response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    init_db()
    data = BridgeService(db).dashboard()
    data['request'] = request
    return templates.TemplateResponse(request=request, name='index.html', context=data)

@app.post('/rally/snapshot')
async def upload_snapshot(file: UploadFile = File(...), db: Session = Depends(get_db)):
    s = get_settings()
    if s.rally_auth_mode != 'browser_snapshot':
        raise HTTPException(400, 'RALLY_AUTH_MODE is not browser_snapshot')
    raw = await file.read()
    try:
        RallySnapshotStore(s.rally_snapshot_file).save_bytes(raw)
    except SnapshotError as exc:
        raise HTTPException(400, str(exc)) from exc
    return RedirectResponse(url='/?snapshot=uploaded', status_code=303)

@app.get('/rally/browser-helper', response_class=HTMLResponse)
def browser_helper_page(request: Request):
    return templates.TemplateResponse(request=request, name='browser_helper.html', context={})

@app.get('/rally/browser-helper.js')
def browser_helper_js():
    return FileResponse(Path(__file__).with_name('browser_helper.js'), media_type='text/javascript', filename='rally-browser-helper.js')

@app.post('/api/import/preview')
def preview(req: ImportRequest, db: Session = Depends(get_db)):
    req.dry_run = True
    return BridgeService(db).execute_import(req)

@app.post('/api/import')
def do_import(req: ImportRequest, db: Session = Depends(get_db)):
    return BridgeService(db).execute_import(req)

@app.post('/api/sync')
def sync(req: SyncRequest, db: Session = Depends(get_db)):
    return BridgeService(db).sync(req)

@app.post('/api/webhooks/gitlab')
def gitlab_webhook(payload: dict, x_gitlab_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    s = get_settings()
    if s.sync_secret and x_gitlab_token != s.sync_secret:
        raise HTTPException(401, 'Invalid webhook token')
    iid = (payload.get('object_attributes') or {}).get('iid')
    if iid:
        from .models import ItemLink
        row = db.query(ItemLink).filter(ItemLink.gitlab_iid == int(iid)).one_or_none()
        if row:
            row.sync_status='pending'; db.commit()
    return {'accepted': True}
