import { config } from './config.js';
import { storiesForScope, summary } from './snapshot.js';
import { getMapping, listMappings, upsertMapping } from './db.js';
import { createIssue, getIssue, updateIssue } from './gitlab.js';

const htmlToText = value => (value || '').replace(/<[^>]*>/g, '').trim();

function storyDescription(story) {
  const bits = [htmlToText(story.Description)];
  bits.push(`\n---\nRally: ${story.FormattedID} · ObjectID ${story.ObjectID}`);
  if (story._bridge?.feature_formatted_id) bits.push(`Feature: ${story._bridge.feature_formatted_id}`);
  return bits.filter(Boolean).join('\n');
}

function taskDescription(task, story) {
  return [htmlToText(task.Description), `\n---\nRally task: ${task.FormattedID}`, `Parent Rally story: ${story.FormattedID}`].filter(Boolean).join('\n');
}

export function preview(type, value) {
  const stories = storiesForScope(type, value);
  return stories.map(story => ({
    formattedId: story.FormattedID,
    name: story.Name,
    objectId: String(story.ObjectID),
    alreadyLinked: Boolean(getMapping(story.ObjectID)),
    tasks: (story._tasks || []).map(task => ({
      formattedId: task.FormattedID,
      name: task.Name,
      objectId: String(task.ObjectID),
      alreadyLinked: Boolean(getMapping(task.ObjectID))
    }))
  }));
}

export async function importScope(type, value, { dryRun = false } = {}) {
  const stories = storiesForScope(type, value);
  const results = [];
  for (const story of stories) {
    let storyMap = getMapping(story.ObjectID);
    if (!storyMap) {
      if (dryRun) {
        storyMap = { rally_formatted_id: story.FormattedID, gitlab_iid: null };
        results.push({ action: 'would-create-story', rally: story.FormattedID });
      } else {
        const issue = await createIssue({
          title: `[${story.FormattedID}] ${story.Name}`,
          description: storyDescription(story),
          labels: ['source::rally', 'bridge::managed']
        });
        storyMap = upsertMapping({
          rally_object_id: String(story.ObjectID), rally_formatted_id: story.FormattedID,
          rally_type: 'story', parent_object_id: null, gitlab_project_id: String(config.gitlabProjectId),
          gitlab_iid: issue.iid, gitlab_type: 'issue'
        });
        results.push({ action: 'created-story', rally: story.FormattedID, gitlabIid: issue.iid });
      }
    } else results.push({ action: 'skipped-story', rally: story.FormattedID, gitlabIid: storyMap.gitlab_iid });

    for (const task of story._tasks || []) {
      if (getMapping(task.ObjectID)) { results.push({ action: 'skipped-task', rally: task.FormattedID }); continue; }
      if (dryRun) { results.push({ action: 'would-create-task', rally: task.FormattedID }); continue; }
      const issue = await createIssue({
        title: `[${task.FormattedID}] ${task.Name}`,
        description: `${taskDescription(task, story)}\nGitLab parent issue: #${storyMap.gitlab_iid}`,
        labels: ['source::rally-task', 'bridge::managed']
      });
      upsertMapping({
        rally_object_id: String(task.ObjectID), rally_formatted_id: task.FormattedID,
        rally_type: 'task', parent_object_id: String(story.ObjectID), gitlab_project_id: String(config.gitlabProjectId),
        gitlab_iid: issue.iid, gitlab_type: 'issue'
      });
      results.push({ action: 'created-task', rally: task.FormattedID, gitlabIid: issue.iid });
    }
  }
  return results;
}

export async function syncScope(type, value, { dryRun = false } = {}) {
  const stories = storiesForScope(type, value);
  const results = [];
  for (const story of stories) {
    const mapping = getMapping(story.ObjectID);
    if (!mapping) { results.push({ status: 'unlinked', rally: story.FormattedID }); continue; }
    const issue = await getIssue(mapping.gitlab_iid);
    const desiredTitle = `[${story.FormattedID}] ${story.Name}`;
    const desiredDescription = storyDescription(story);
    const changes = {};
    if (issue.title !== desiredTitle) changes.title = desiredTitle;
    if (issue.description !== desiredDescription) changes.description = desiredDescription;
    if (Object.keys(changes).length) {
      if (!dryRun) await updateIssue(mapping.gitlab_iid, changes);
      results.push({ status: dryRun ? 'would-update-gitlab' : 'updated-gitlab', rally: story.FormattedID, changes });
    } else results.push({ status: 'in-sync', rally: story.FormattedID });

    // GitLab-owned state/assignee/estimate cannot be written back through browser snapshot mode.
    results.push({
      status: 'rally-update-required', rally: story.FormattedID,
      rallyUpdate: { formattedId: story.FormattedID, fields: { state: issue.state, assignee: issue.assignee?.username || null } }
    });
  }
  return results;
}

export function status() {
  return { version: '0.3.0', snapshot: summary(), mappings: listMappings() };
}
