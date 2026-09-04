import json
from app.snapshot import RallySnapshotStore

def test_snapshot_queries(tmp_path):
    path = tmp_path / 'rally.json'; store = RallySnapshotStore(str(path))
    data = {'version':1,'source':'rally-browser-session','scope':{'type':'feature','value':'F100'},'stories':[{'ObjectID':10,'FormattedID':'US10','Name':'Story','_bridge':{'feature_formatted_id':'F100'},'_tasks':[{'ObjectID':20,'FormattedID':'TA20','Name':'Task'}]}]}
    store.save_bytes(json.dumps(data).encode())
    assert store.get_story('US10')['ObjectID'] == 10
    assert store.stories_for_feature('F100')[0]['FormattedID'] == 'US10'
    assert store.tasks_for_story('10')[0]['FormattedID'] == 'TA20'
