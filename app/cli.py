import json
import typer
from .db import SessionLocal, init_db
from .schemas import ImportRequest, SyncRequest
from .service import BridgeService

app = typer.Typer(help='Selective Rally ↔ GitLab migration and sync utility')

def dump(x): typer.echo(json.dumps(x, indent=2, default=str))

@app.command()
def preview(scope_type: str, scope_value: str, include_tasks: bool=True, squad_only: bool=True):
    init_db()
    with SessionLocal() as db:
        dump(BridgeService(db).execute_import(ImportRequest(scope_type=scope_type, scope_value=scope_value, include_tasks=include_tasks, squad_only=squad_only, dry_run=True)))

@app.command('import')
def import_items(scope_type: str, scope_value: str, include_tasks: bool=True, squad_only: bool=True):
    init_db()
    with SessionLocal() as db:
        dump(BridgeService(db).execute_import(ImportRequest(scope_type=scope_type, scope_value=scope_value, include_tasks=include_tasks, squad_only=squad_only, dry_run=False)))

@app.command()
def sync(scope_type: str='all', scope_value: str|None=None, direction: str='reconcile', dry_run: bool=False):
    init_db()
    with SessionLocal() as db:
        dump(BridgeService(db).sync(SyncRequest(scope_type=scope_type, scope_value=scope_value, direction=direction, dry_run=dry_run)))

@app.command()
def status():
    init_db()
    with SessionLocal() as db: dump(BridgeService(db).dashboard())
