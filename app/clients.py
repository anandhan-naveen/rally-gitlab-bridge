from __future__ import annotations
import httpx
from urllib.parse import quote
from .config import get_settings

class RallyClient:
    def __init__(self):
        s = get_settings(); self.base = s.rally_base_url.rstrip('/') + '/slm/webservice/v2.0'; self.workspace_oid = s.rally_workspace_oid; self.project_oid = s.rally_project_oid
        self.client = httpx.Client(timeout=60, headers={'zsessionid': s.rally_api_key, 'Content-Type': 'application/json'})
    @property
    def workspace_ref(self): return f'/workspace/{self.workspace_oid}'
    def _query(self, endpoint: str, query: str, fetch: str = 'true') -> list[dict]:
        start, size, out = 1, 200, []
        while True:
            r = self.client.get(f'{self.base}/{endpoint}', params={'workspace':self.workspace_ref,'project':f'/project/{self.project_oid}' if self.project_oid else None,'projectScopeDown':'true','projectScopeUp':'false','query':query,'fetch':fetch,'start':start,'pagesize':size}); r.raise_for_status(); qr=r.json()['QueryResult']; out.extend(qr.get('Results', []))
            if len(out) >= qr.get('TotalResultCount',0): break
            start += size
        return out
    def get_story(self, formatted_id):
        rows=self._query('hierarchicalrequirement', f'(FormattedID = "{formatted_id}")'); return rows[0] if rows else None
    def get_feature(self, formatted_id):
        rows=self._query('portfolioitem/feature', f'(FormattedID = "{formatted_id}")'); return rows[0] if rows else None
    def stories_for_feature(self, formatted_id):
        feature=self.get_feature(formatted_id)
        if not feature: return []
        return self._query('hierarchicalrequirement', f'(PortfolioItem = /portfolioitem/feature/{feature["ObjectID"]})', 'ObjectID,FormattedID,Name,Description,ScheduleState,PlanEstimate,Owner,Project,Iteration,Release,PortfolioItem,LastUpdateDate,Tasks')
    def stories_for_quarter(self, quarter, quarter_field): return self._query('hierarchicalrequirement', f'({quarter_field} = "{quarter}")', 'ObjectID,FormattedID,Name,Description,ScheduleState,PlanEstimate,Owner,Project,Iteration,Release,PortfolioItem,LastUpdateDate,Tasks,'+quarter_field)
    def tasks_for_story(self, story_oid): return self._query('task', f'(WorkProduct = /hierarchicalrequirement/{story_oid})', 'ObjectID,FormattedID,Name,Description,State,Estimate,Actuals,Owner,WorkProduct,LastUpdateDate')
    def update_story(self, oid, fields):
        r=self.client.post(f'{self.base}/hierarchicalrequirement/{oid}',json={'HierarchicalRequirement':fields}); r.raise_for_status(); return r.json()
    def update_task(self, oid, fields):
        r=self.client.post(f'{self.base}/task/{oid}',json={'Task':fields}); r.raise_for_status(); return r.json()

class GitLabClient:
    def __init__(self):
        s=get_settings(); self.base=s.gitlab_base_url.rstrip('/'); self.project_id=s.gitlab_project_id; self.project_path=s.gitlab_project_path; self.headers={'PRIVATE-TOKEN':s.gitlab_token}; self.bearer={'Authorization':f'Bearer {s.gitlab_token}'}; self.client=httpx.Client(timeout=60)
    def _rest(self, method, path, **kwargs):
        r=self.client.request(method,f'{self.base}/api/v4{path}',headers=self.headers,**kwargs); r.raise_for_status(); return r.json() if r.content else {}
    def graphql(self, query, variables=None):
        r=self.client.post(f'{self.base}/api/graphql',headers=self.bearer,json={'query':query,'variables':variables or {}}); r.raise_for_status(); body=r.json()
        if body.get('errors'): raise RuntimeError(body['errors'])
        return body['data']
    def create_issue(self,title,description,labels=None,weight=None):
        payload={'title':title,'description':description,'labels':','.join(labels or [])}
        if weight is not None: payload['weight']=weight
        return self._rest('POST',f'/projects/{quote(str(self.project_id),safe="")}/issues',data=payload)
    def get_issue(self,iid): return self._rest('GET',f'/projects/{quote(str(self.project_id),safe="")}/issues/{iid}')
    def update_issue(self,iid,**fields): return self._rest('PUT',f'/projects/{quote(str(self.project_id),safe="")}/issues/{iid}',data=fields)
    def work_item_type_id(self,name):
        q='''query($path: ID!, $name: IssueType){ namespace(fullPath:$path){ workItemTypes(name:$name){ nodes{id name} } } }'''; nodes=self.graphql(q,{'path':self.project_path,'name':name.upper()})['namespace']['workItemTypes']['nodes']
        if not nodes: raise RuntimeError(f'GitLab work item type {name} is unavailable in {self.project_path}')
        return nodes[0]['id']
    def get_work_item(self,iid):
        q='''query($path: ID!, $iid: String!){ namespace(fullPath:$path){ workItem(iid:$iid){ id iid title state webUrl widgets{ ... on WorkItemWidgetDescription { description } ... on WorkItemWidgetAssignees { assignees { nodes { id username name } } } } } } }'''; return self.graphql(q,{'path':self.project_path,'iid':str(iid)})['namespace']['workItem']
    def create_task(self,title,description,parent_work_item_id):
        type_id=self.work_item_type_id('TASK'); q='''mutation($input: WorkItemCreateInput!){ workItemCreate(input:$input){ workItem{ id iid title webUrl } errors } }'''; inp={'title':title,'namespacePath':self.project_path,'workItemTypeId':type_id,'descriptionWidget':{'description':description},'hierarchyWidget':{'parentId':parent_work_item_id}}; result=self.graphql(q,{'input':inp})['workItemCreate']
        if result.get('errors'): raise RuntimeError(result['errors'])
        return result['workItem']
    def update_work_item(self,work_item_id,title=None,description=None):
        q='''mutation($input: WorkItemUpdateInput!){ workItemUpdate(input:$input){ workItem{ id iid title state } errors } }'''; inp={'id':work_item_id}
        if title is not None: inp['title']=title
        if description is not None: inp['descriptionWidget']={'description':description}
        result=self.graphql(q,{'input':inp})['workItemUpdate']
        if result.get('errors'): raise RuntimeError(result['errors'])
        return result['workItem']
