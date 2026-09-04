import json
from fastapi.testclient import TestClient
from app.main import app

def test_dashboard_renders():
    with TestClient(app) as client:
        r=client.get('/'); assert r.status_code==200; assert 'Rally' in r.text; assert 'Browser SSO POC mode' in r.text

def test_health():
    with TestClient(app) as client:
        r=client.get('/health'); assert r.status_code==200; assert r.json()['status']=='ok'; assert r.json()['version']=='0.2.0'

def test_browser_helper_page():
    with TestClient(app) as client:
        r=client.get('/rally/browser-helper'); assert r.status_code==200; assert 'does <strong>not</strong>' in r.text; assert 'API key' in r.text

def test_snapshot_upload(tmp_path, monkeypatch):
    from app.config import get_settings
    s=get_settings(); old=s.rally_snapshot_file; s.rally_snapshot_file=str(tmp_path/'snapshot.json')
    try:
        snapshot={'version':1,'source':'rally-browser-session','captured_at':'2026-09-04T10:00:00Z','scope':{'type':'feature','value':'F123'},'stories':[{'ObjectID':1,'FormattedID':'US1','Name':'Test','_tasks':[{'ObjectID':2,'FormattedID':'TA1','Name':'Task'}]}]}
        with TestClient(app) as client:
            r=client.post('/rally/snapshot',files={'file':('snapshot.json',json.dumps(snapshot),'application/json')},follow_redirects=False); assert r.status_code==303; assert (tmp_path/'snapshot.json').exists()
    finally: s.rally_snapshot_file=old
