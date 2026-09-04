from __future__ import annotations
import json
from pathlib import Path

class SnapshotError(ValueError):
    pass

class RallySnapshotStore:
    def __init__(self, path: str = 'data/rally_snapshot.json'):
        self.path = Path(path)

    def save_bytes(self, raw: bytes) -> dict:
        try:
            data = json.loads(raw.decode('utf-8'))
        except Exception as exc:
            raise SnapshotError(f'Invalid JSON snapshot: {exc}') from exc
        self.validate(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding='utf-8')
        return self.summary(data)

    def load(self) -> dict | None:
        if not self.path.exists(): return None
        data = json.loads(self.path.read_text(encoding='utf-8'))
        self.validate(data); return data

    def validate(self, data: dict):
        if not isinstance(data, dict): raise SnapshotError('Snapshot must be a JSON object')
        if data.get('source') != 'rally-browser-session': raise SnapshotError('This is not a Rally browser-session snapshot')
        if not isinstance(data.get('stories'), list): raise SnapshotError('Snapshot is missing the stories array')
        for story in data['stories']:
            if not story.get('ObjectID') or not story.get('FormattedID'): raise SnapshotError('Every story must contain ObjectID and FormattedID')
            if '_tasks' in story and not isinstance(story['_tasks'], list): raise SnapshotError('_tasks must be an array')

    def summary(self, data: dict | None = None) -> dict:
        data = data or self.load()
        if not data: return {'available': False, 'stories': 0, 'tasks': 0}
        stories = data.get('stories', [])
        return {'available': True, 'captured_at': data.get('captured_at'), 'scope': data.get('scope') or {}, 'stories': len(stories), 'tasks': sum(len(x.get('_tasks', [])) for x in stories), 'workspace': (data.get('workspace') or {}).get('Name'), 'project': (data.get('project') or {}).get('Name')}

    def get_story(self, formatted_id: str) -> dict | None:
        return next((s for s in (self.load() or {}).get('stories', []) if s.get('FormattedID') == formatted_id), None)

    def stories_for_feature(self, formatted_id: str) -> list[dict]:
        data = self.load() or {}; scope = data.get('scope') or {}
        if scope.get('type') == 'feature' and scope.get('value') == formatted_id: return data.get('stories', [])
        return [s for s in data.get('stories', []) if (s.get('_bridge') or {}).get('feature_formatted_id') == formatted_id]

    def stories_for_quarter(self, quarter: str, quarter_field: str) -> list[dict]:
        data = self.load() or {}; scope = data.get('scope') or {}
        if scope.get('type') == 'quarter' and scope.get('value') == quarter: return data.get('stories', [])
        return [s for s in data.get('stories', []) if str(s.get(quarter_field) or '') == quarter]

    def tasks_for_story(self, story_oid: str) -> list[dict]:
        for story in (self.load() or {}).get('stories', []):
            if str(story.get('ObjectID')) == str(story_oid): return story.get('_tasks', [])
        return []

    def get_task(self, formatted_id: str) -> dict | None:
        for story in (self.load() or {}).get('stories', []):
            for task in story.get('_tasks', []):
                if task.get('FormattedID') == formatted_id: return task
        return None
