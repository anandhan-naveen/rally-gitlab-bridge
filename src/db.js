import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';
import { config } from './config.js';

fs.mkdirSync(path.dirname(config.databaseFile), { recursive: true });
export const db = new Database(config.databaseFile);

db.exec(`
CREATE TABLE IF NOT EXISTS mappings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rally_object_id TEXT NOT NULL UNIQUE,
  rally_formatted_id TEXT NOT NULL,
  rally_type TEXT NOT NULL,
  parent_object_id TEXT,
  gitlab_project_id TEXT,
  gitlab_iid INTEGER,
  gitlab_type TEXT,
  status TEXT NOT NULL DEFAULT 'linked',
  last_error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
`);

export function getMapping(objectId) {
  return db.prepare('SELECT * FROM mappings WHERE rally_object_id = ?').get(String(objectId));
}

export function upsertMapping(m) {
  db.prepare(`
    INSERT INTO mappings (rally_object_id, rally_formatted_id, rally_type, parent_object_id, gitlab_project_id, gitlab_iid, gitlab_type, status, last_error)
    VALUES (@rally_object_id,@rally_formatted_id,@rally_type,@parent_object_id,@gitlab_project_id,@gitlab_iid,@gitlab_type,@status,@last_error)
    ON CONFLICT(rally_object_id) DO UPDATE SET
      rally_formatted_id=excluded.rally_formatted_id,
      rally_type=excluded.rally_type,
      parent_object_id=excluded.parent_object_id,
      gitlab_project_id=excluded.gitlab_project_id,
      gitlab_iid=excluded.gitlab_iid,
      gitlab_type=excluded.gitlab_type,
      status=excluded.status,
      last_error=excluded.last_error,
      updated_at=CURRENT_TIMESTAMP
  `).run({ status: 'linked', last_error: null, ...m });
  return getMapping(m.rally_object_id);
}

export function listMappings() {
  return db.prepare('SELECT * FROM mappings ORDER BY updated_at DESC').all();
}
