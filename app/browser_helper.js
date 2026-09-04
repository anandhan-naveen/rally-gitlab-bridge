(async () => {
  const VERSION = '0.2.0';
  const api = location.origin + '/slm/webservice/v2.0';
  const scopeType = (prompt('Scope type: quarter, feature, or story', 'feature') || '').trim().toLowerCase();
  if (!['quarter', 'feature', 'story'].includes(scopeType)) { alert('Cancelled: scope type must be quarter, feature, or story.'); return; }
  const scopeValue = (prompt(`Enter ${scopeType} value (for example F1234, US1234, or Q4-2026)`, '') || '').trim();
  if (!scopeValue) { alert('Cancelled: no scope value.'); return; }
  const quarterField = scopeType === 'quarter' ? ((prompt('Rally internal quarter field name', 'c_Quarter') || 'c_Quarter').trim()) : 'c_Quarter';
  const fetchFields = ['ObjectID','FormattedID','Name','Description','ScheduleState','PlanEstimate','Owner','Project','Iteration','Release','PortfolioItem','LastUpdateDate','Tasks', quarterField].join(',');
  async function query(endpoint, queryText, fields = 'true') {
    const all = []; let start = 1; const pagesize = 200;
    while (true) {
      const u = new URL(`${api}/${endpoint}`); u.searchParams.set('query', queryText); u.searchParams.set('fetch', fields); u.searchParams.set('start', String(start)); u.searchParams.set('pagesize', String(pagesize)); u.searchParams.set('projectScopeDown', 'true'); u.searchParams.set('projectScopeUp', 'false');
      const r = await window.fetch(u, {credentials: 'include', headers: {'Accept':'application/json'}});
      if (!r.ok) throw new Error(`${endpoint}: HTTP ${r.status} ${await r.text()}`);
      const qr = (await r.json()).QueryResult; all.push(...(qr.Results || []));
      if (all.length >= (qr.TotalResultCount || 0)) break; start += pagesize;
    }
    return all;
  }
  try {
    let stories = [];
    if (scopeType === 'story') stories = await query('hierarchicalrequirement', `(FormattedID = "${scopeValue.replaceAll('"','\\"')}")`, fetchFields);
    else if (scopeType === 'feature') {
      const f = await query('portfolioitem/feature', `(FormattedID = "${scopeValue.replaceAll('"','\\"')}")`, 'ObjectID,FormattedID,Name,Project');
      if (!f.length) throw new Error(`Feature ${scopeValue} was not found.`);
      stories = await query('hierarchicalrequirement', `(PortfolioItem = /portfolioitem/feature/${f[0].ObjectID})`, fetchFields);
      for (const s of stories) s._bridge = {...(s._bridge || {}), feature_formatted_id: scopeValue};
    } else stories = await query('hierarchicalrequirement', `(${quarterField} = "${scopeValue.replaceAll('"','\\"')}")`, fetchFields);
    for (let i = 0; i < stories.length; i++) { const s = stories[i]; s._tasks = await query('task', `(WorkProduct = /hierarchicalrequirement/${s.ObjectID})`, 'ObjectID,FormattedID,Name,Description,State,Estimate,Actuals,Owner,WorkProduct,LastUpdateDate'); console.log(`Rally Bridge: ${i+1}/${stories.length} ${s.FormattedID} (${s._tasks.length} tasks)`); }
    const snapshot = {version: 1, helper_version: VERSION, source: 'rally-browser-session', captured_at: new Date().toISOString(), rally_origin: location.origin, scope: {type: scopeType, value: scopeValue, quarter_field: quarterField}, stories};
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], {type: 'application/json'}); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `rally-${scopeType}-${scopeValue.replace(/[^a-z0-9_-]+/gi,'_')}.json`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    alert(`Rally snapshot created: ${stories.length} stories. Upload the downloaded JSON to http://127.0.0.1:8000.`);
  } catch (e) { console.error('Rally Bridge helper failed', e); alert(`Rally snapshot failed: ${e.message}\n\nNo Rally data was changed.`); }
})();
