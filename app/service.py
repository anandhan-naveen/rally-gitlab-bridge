from __future__ import annotations
from datetime import datetime
from pathlib import Path
import yaml
from sqlalchemy.orm import Session
from .clients import RallyClient, GitLabClient
from .config import get_settings
from .models import ItemLink, SyncLog
from .schemas import ImportPlan, ImportRequest, SyncRequest
from .snapshot import RallySnapshotStore

def _ref_name(value):
    if not value: return None
    if isinstance(value, dict): return value.get('_refObjectName') or value.get('Name')
    return str(value)

class BridgeService:
    def __init__(self, db: Session):
        self.db=db; self.s=get_settings(); self.snapshot=RallySnapshotStore(self.s.rally_snapshot_file); self.rally=RallyClient() if self.s.rally_auth_mode!='browser_snapshot' else None; self.gitlab=GitLabClient(); p=Path(self.s.config_file); self.cfg=yaml.safe_load(p.read_text()) if p.exists() else {}
    def _story_in_squad(self,story):
        if not self.s.rally_squad_value: return True
        field=self.s.rally_squad_field; actual=_ref_name(story.get(field))
        if actual is None and field=='Project': actual=_ref_name(story.get('Project'))
        return str(actual or '').strip().lower()==self.s.rally_squad_value.strip().lower()
    def _linked(self,oid): return self.db.query(ItemLink).filter(ItemLink.rally_object_id==str(oid)).one_or_none()
    def _scope_stories(self,req):
        source=self.snapshot if self.s.rally_auth_mode=='browser_snapshot' else self.rally
        if req.scope_type=='quarter': return source.stories_for_quarter(req.scope_value,self.s.rally_quarter_field)
        if req.scope_type=='feature': return source.stories_for_feature(req.scope_value)
        story=source.get_story(req.scope_value); return [story] if story else []
    def plan_import(self,req):
        stories=self._scope_stories(req); selected=[x for x in stories if not req.squad_only or self._story_in_squad(x)]; items=[]; tasks_found=linked=0
        for story in selected:
            is_linked=bool(self._linked(story['ObjectID'])); linked+=int(is_linked); source=self.snapshot if self.s.rally_auth_mode=='browser_snapshot' else self.rally; tasks=source.tasks_for_story(str(story['ObjectID'])) if req.include_tasks else []; tasks_found+=len(tasks); items.append({'formatted_id':story.get('FormattedID'),'name':story.get('Name'),'rally_oid':str(story.get('ObjectID')),'linked':is_linked,'project':_ref_name(story.get('Project')),'feature':_ref_name(story.get('PortfolioItem')),'task_count':len(tasks)})
        return ImportPlan(scope=f'{req.scope_type}:{req.scope_value}',stories_found=len(stories),squad_stories=len(selected),tasks_found=tasks_found,already_linked=linked,to_create=len(selected)-linked,excluded=len(stories)-len(selected),items=items)
    @staticmethod
    def _rally_marker(item): return f"Rally: {item.get('FormattedID')} · ObjectID {item.get('ObjectID')}"
    def _story_description(self,story): return f"{story.get('Description') or ''}\n\n---\n**Managed by Rally ↔ GitLab Bridge**  \n{self._rally_marker(story)}  \nFeature: {_ref_name(story.get('PortfolioItem')) or '—'}  \nRally project/squad: {_ref_name(story.get('Project')) or '—'}"
    def _task_description(self,task): return f"{task.get('Description') or ''}\n\n---\n**Managed by Rally ↔ GitLab Bridge**  \n{self._rally_marker(task)}"
    def execute_import(self,req):
        plan=self.plan_import(req)
        if req.dry_run: return {'dry_run':True,'plan':plan.model_dump()}
        stories=[x for x in self._scope_stories(req) if not req.squad_only or self._story_in_squad(x)]; created=[]; skipped=[]; errors=[]; labels_cfg=self.cfg.get('labels',{})
        for story in stories:
            try:
                if self._linked(story['ObjectID']): skipped.append(story.get('FormattedID')); continue
                gl=self.gitlab.create_issue(title=f"[{story.get('FormattedID')}] {story.get('Name')}",description=self._story_description(story),labels=[labels_cfg.get('rally_story','source::rally'),labels_cfg.get('managed','bridge::managed')],weight=story.get('PlanEstimate'))
                self.db.add(ItemLink(rally_object_id=str(story['ObjectID']),rally_formatted_id=story.get('FormattedID',''),rally_type='story',gitlab_project_id=str(self.s.gitlab_project_id),gitlab_iid=int(gl['iid']),gitlab_type='issue',last_rally_updated=story.get('LastUpdateDate'),last_gitlab_updated=gl.get('updated_at'),last_sync_at=datetime.utcnow(),sync_status='synced')); self.db.commit(); created.append({'rally':story.get('FormattedID'),'gitlab_iid':gl['iid']})
                if req.include_tasks:
                    parent_wi=self.gitlab.get_work_item(int(gl['iid'])); source=self.snapshot if self.s.rally_auth_mode=='browser_snapshot' else self.rally
                    for task in source.tasks_for_story(str(story['ObjectID'])):
                        if self._linked(task['ObjectID']): continue
                        tw=self.gitlab.create_task(f"[{task.get('FormattedID')}] {task.get('Name')}",self._task_description(task),parent_wi['id']); self.db.add(ItemLink(rally_object_id=str(task['ObjectID']),rally_formatted_id=task.get('FormattedID',''),rally_type='task',rally_parent_object_id=str(story['ObjectID']),gitlab_project_id=str(self.s.gitlab_project_id),gitlab_iid=int(tw['iid']),gitlab_type='task',last_rally_updated=task.get('LastUpdateDate'),last_sync_at=datetime.utcnow(),sync_status='synced')); self.db.commit()
            except Exception as exc: self.db.rollback(); errors.append({'rally':story.get('FormattedID'),'error':str(exc)})
        self.db.add(SyncLog(operation='import',scope=plan.scope,status='ok' if not errors else 'partial',detail=str({'created':created,'errors':errors}))); self.db.commit(); return {'dry_run':False,'created':created,'skipped':skipped,'errors':errors,'plan':plan.model_dump()}
    def _fetch_rally_linked(self,link):
        if self.s.rally_auth_mode=='browser_snapshot': return self.snapshot.get_story(link.rally_formatted_id) if link.rally_type=='story' else self.snapshot.get_task(link.rally_formatted_id)
        if link.rally_type=='story': return self.rally.get_story(link.rally_formatted_id)
        rows=self.rally._query('task',f'(FormattedID = "{link.rally_formatted_id}")'); return rows[0] if rows else None
    def sync_link(self,link,direction='reconcile',dry_run=False):
        rally=self._fetch_rally_linked(link)
        if not rally: return {'id':link.rally_formatted_id,'status':'error','error':'Rally item not found'}
        gl=self.gitlab.get_issue(link.gitlab_iid) if link.gitlab_type=='issue' else self.gitlab.get_work_item(link.gitlab_iid); ownership=self.cfg.get('field_ownership',{}); changes=[]
        def allow(owner): return direction=='reconcile' or direction==('rally_to_gitlab' if owner=='rally' else 'gitlab_to_rally')
        if allow('rally'):
            if ownership.get('title')=='rally':
                expected=f"[{rally.get('FormattedID')}] {rally.get('Name')}"
                if gl.get('title')!=expected: changes.append(('gitlab','title',expected))
            if ownership.get('description')=='rally':
                expected=self._story_description(rally) if link.rally_type=='story' else self._task_description(rally); current=gl.get('description')
                if current is None and link.gitlab_type=='task':
                    for w in gl.get('widgets',[]):
                        if 'description' in w: current=w.get('description')
                if current!=expected: changes.append(('gitlab','description',expected))
        if allow('gitlab') and ownership.get('state')=='gitlab' and link.rally_type=='story':
            target=self.cfg.get('state_mapping',{}).get('gitlab_to_rally',{}).get(gl.get('state'))
            if target and rally.get('ScheduleState')!=target: changes.append(('rally','ScheduleState',target))
        if not dry_run:
            gl_fields={f:v for t,f,v in changes if t=='gitlab'}; rally_fields={f:v for t,f,v in changes if t=='rally'}
            if gl_fields:
                if link.gitlab_type=='issue': self.gitlab.update_issue(link.gitlab_iid,**gl_fields)
                else:
                    wi=self.gitlab.get_work_item(link.gitlab_iid); self.gitlab.update_work_item(wi['id'],title=gl_fields.get('title'),description=gl_fields.get('description'))
            if rally_fields:
                if self.s.rally_auth_mode=='browser_snapshot': return {'id':link.rally_formatted_id,'gitlab_iid':link.gitlab_iid,'status':'rally_update_required','changes':changes,'rally_update':{'type':link.rally_type,'object_id':link.rally_object_id,'formatted_id':link.rally_formatted_id,'fields':rally_fields}}
                (self.rally.update_story if link.rally_type=='story' else self.rally.update_task)(link.rally_object_id,rally_fields)
            link.last_sync_at=datetime.utcnow(); link.sync_status='synced'; link.last_error=None; self.db.commit()
        return {'id':link.rally_formatted_id,'gitlab_iid':link.gitlab_iid,'status':'planned' if dry_run else 'synced','changes':changes}
    def sync(self,req):
        links=self.db.query(ItemLink).all()
        if req.scope_type in ('feature','quarter') and req.scope_value:
            ids={x['rally_oid'] for x in self.plan_import(ImportRequest(scope_type=req.scope_type,scope_value=req.scope_value,include_tasks=True,squad_only=True,dry_run=True)).items}; links=[l for l in links if l.rally_object_id in ids or l.rally_parent_object_id in ids]
        elif req.scope_type=='story' and req.scope_value:
            story_link=next((l for l in links if l.rally_formatted_id==req.scope_value and l.rally_type=='story'),None); links=[l for l in links if story_link and (l.id==story_link.id or l.rally_parent_object_id==story_link.rally_object_id)]
        results=[]
        for link in links:
            try: results.append(self.sync_link(link,req.direction,req.dry_run))
            except Exception as exc: self.db.rollback(); link.sync_status='error'; link.last_error=str(exc); self.db.commit(); results.append({'id':link.rally_formatted_id,'status':'error','error':str(exc)})
        return {'count':len(results),'dry_run':req.dry_run,'results':results}
    def dashboard(self):
        links=self.db.query(ItemLink).all(); snap=self.snapshot.summary() if self.s.rally_auth_mode=='browser_snapshot' else {'available':False}
        return {'auth_mode':self.s.rally_auth_mode,'snapshot':snap,'linked':len(links),'synced':sum(x.sync_status=='synced' for x in links),'errors':sum(x.sync_status=='error' for x in links),'stories':sum(x.rally_type=='story' for x in links),'tasks':sum(x.rally_type=='task' for x in links),'items':links[-100:]}
