from app.schemas import ImportRequest, SyncRequest

def test_import_request():
    x=ImportRequest(scope_type='feature', scope_value='F123', dry_run=True)
    assert x.include_tasks is True

def test_sync_request():
    x=SyncRequest(scope_type='all')
    assert x.direction == 'reconcile'
