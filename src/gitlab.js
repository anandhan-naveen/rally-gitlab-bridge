import { config } from './config.js';

function headers() {
  if (!config.gitlabToken) throw new Error('GITLAB_TOKEN is not configured.');
  return { 'PRIVATE-TOKEN': config.gitlabToken, 'Content-Type': 'application/json' };
}

function projectId() {
  if (!config.gitlabProjectId) throw new Error('GITLAB_PROJECT_ID is not configured.');
  return encodeURIComponent(config.gitlabProjectId);
}

export async function createIssue({ title, description, labels = [] }) {
  const r = await fetch(`${config.gitlabBaseUrl}/api/v4/projects/${projectId()}/issues`, {
    method: 'POST', headers: headers(),
    body: JSON.stringify({ title, description, labels: labels.join(',') })
  });
  if (!r.ok) throw new Error(`GitLab issue create failed: ${r.status} ${await r.text()}`);
  return r.json();
}

export async function getIssue(iid) {
  const r = await fetch(`${config.gitlabBaseUrl}/api/v4/projects/${projectId()}/issues/${iid}`, { headers: headers() });
  if (!r.ok) throw new Error(`GitLab issue fetch failed: ${r.status} ${await r.text()}`);
  return r.json();
}

export async function updateIssue(iid, fields) {
  const r = await fetch(`${config.gitlabBaseUrl}/api/v4/projects/${projectId()}/issues/${iid}`, {
    method: 'PUT', headers: headers(), body: JSON.stringify(fields)
  });
  if (!r.ok) throw new Error(`GitLab issue update failed: ${r.status} ${await r.text()}`);
  return r.json();
}
