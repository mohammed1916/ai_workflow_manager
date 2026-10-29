// Observation scope and pair outcomes are different dimensions, never interchangeable.
export function observationInventory(project, pairs = []) {
  const rows = (project.papers || []).flatMap(paper => (paper.metrics || []).map(metric => {
    const scope = metric.outcomeId === 'outside_scope' ? 'outside' :
      (metric.protocol?.outcomes?.some(o => o.id === metric.outcomeId) ? 'assigned' : 'unresolved');
    const labels = Object.fromEntries((metric.protocol?.factors || []).map(f => [f.key, f.label]));
    Object.assign(labels, {entityId:'Entity membership', outcomeId:'Requested outcome', measurementQuote:'Measurement definition'});
    return {key:paper.id+':'+metric.id, paper:paper.id, title:paper.title, metric:metric.id,
      method:metric.method, name:metric.name, value:metric.value, unit:metric.unit,
      quote:metric.quote || '', outcomeQuote:metric.outcomeQuote || '', scope,
      missing:(metric.missing || []).map(k => labels[k] || k),
      assessments:[], comparisons:{comparable:0,incompatible:0,insufficient:0,pending:0}};
  }));
  const index = new Map(rows.map(row => [row.key,row]));
  for (const pair of pairs) {
    const bucket = pair.assessed ? pair.outcome : 'pending';
    for (const key of new Set(['a','b'].map(side => pair[side].paper+':'+pair[side].metric))) {
      const row = index.get(key);
      if (row && Object.hasOwn(row.comparisons,bucket)) {
        row.comparisons[bucket]++;
        if (pair.assessed) {
          const other=pair.a.paper+':'+pair.a.metric===key?pair.b:pair.a;
          row.assessments.push({id:pair.id,outcome:pair.outcome,other:[other.method,other.name,other.value].filter(Boolean).join(' '),reasons:pair.explanation||[]});
        }
      }
    }
  }
  return {rows, total:rows.length, labels:new Set(rows.map(r=>r.name)).size,
    assigned:rows.filter(r=>r.scope==='assigned').length,
    outside:rows.filter(r=>r.scope==='outside').length,
    unresolved:rows.filter(r=>r.scope==='unresolved').length};
}
