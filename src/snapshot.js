import fs from 'node:fs';
import path from 'node:path';
import { config } from './config.js';

export function validateSnapshot(data) {
  if (!data || typeof data !== 'object') throw new Error('Snapshot must be a JSON object.');
  if (data.source !== 'rally-browser-session') throw new Error('Unsupported snapshot source.');
  if (!Array.isArray(data.stories)) throw new Error('Snapshot stories must be an array.');
  for (const story of data.stories) {
    if (!story.ObjectID || !story.FormattedID) throw new Error('Each story needs ObjectID and FormattedID.');
    if (story._tasks && !Array.isArray(story._tasks)) throw new Error('_tasks must be an array.');
  }
  return data;
}

export function saveSnapshot(data) {
  validateSnapshot(data);
  fs.mkdirSync(path.dirname(config.rallySnapshotFile), { recursive: true });
  fs.writeFileSync(config.rallySnapshotFile, JSON.stringify(data, null, 2));
  return summary(data);
}

export function loadSnapshot() {
  if (!fs.existsSync(config.rallySnapshotFile)) return null;
  return validateSnapshot(JSON.parse(fs.readFileSync(config.rallySnapshotFile, 'utf8')));
}

export function summary(data = loadSnapshot()) {
  if (!data) return { available: false, stories: 0, tasks: 0 };
  return {
    available: true,
    capturedAt: data.captured_at || null,
    scope: data.scope || null,
    stories: data.stories.length,
    tasks: data.stories.reduce((n, s) => n + (s._tasks?.length || 0), 0)
  };
}

export function storiesForScope(type, value) {
  const data = loadSnapshot();
  if (!data) throw new Error('No Rally snapshot loaded.');
  let stories = data.stories;
  if (config.rallySquadValue) {
    stories = stories.filter(s => {
      const v = s[config.rallySquadField];
      const name = typeof v === 'object' ? (v?._refObjectName || v?.Name) : v;
      return name === config.rallySquadValue;
    });
  }
  if (type === 'story') return stories.filter(s => s.FormattedID === value);
  if (type === 'feature') return stories.filter(s => s._bridge?.feature_formatted_id === value || s.PortfolioItem?.FormattedID === value);
  if (type === 'quarter') return stories.filter(s => s[config.rallyQuarterField] === value);
  if (type === 'all') return stories;
  throw new Error(`Unsupported scope: ${type}`);
}
