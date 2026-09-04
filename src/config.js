import 'dotenv/config';

export const config = {
  port: Number(process.env.PORT || 8000),
  databaseFile: process.env.DATABASE_FILE || 'data/bridge.db',
  rallySnapshotFile: process.env.RALLY_SNAPSHOT_FILE || 'data/rally_snapshot.json',
  rallySquadField: process.env.RALLY_SQUAD_FIELD || 'Project',
  rallySquadValue: process.env.RALLY_SQUAD_VALUE || '',
  rallyQuarterField: process.env.RALLY_QUARTER_FIELD || 'c_Quarter',
  gitlabBaseUrl: (process.env.GITLAB_BASE_URL || '').replace(/\/$/, ''),
  gitlabToken: process.env.GITLAB_TOKEN || '',
  gitlabProjectId: process.env.GITLAB_PROJECT_ID || '',
  gitlabProjectPath: process.env.GITLAB_PROJECT_PATH || '',
  syncSecret: process.env.SYNC_SECRET || ''
};
