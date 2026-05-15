const BASE = import.meta.env.DEV ? 'http://localhost:7070' : '';

async function get(path) {
  const r = await fetch(BASE + path);
  if (!r.ok) throw new Error(`API error: ${r.status} ${path}`);
  return r.json();
}

async function post(path, body) {
  const r = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`API error: ${r.status} ${path}`);
  return r.json();
}

export const getTenants = () => get('/api/tenants');
export const getTenantHosts = (name) => get(`/api/tenants/${name}/hosts`);
export const getOperations = () => get('/api/operations');
export const getHostConfig = (tenant, host) => get(`/api/tenants/${tenant}/hosts/${host}/config`);
export const getTopology = (tenant) => get(`/api/tenants/${tenant}/topology`);
export const getLocations = (tenant) => get(`/api/tenants/${tenant}/locations`);
export const getServices = (tenant) => get(`/api/tenants/${tenant}/services`);
export const getServiceDetail = (tenant, name) => get(`/api/tenants/${tenant}/services/${name}`);
export const getHostServices = (tenant, host) => get(`/api/tenants/${tenant}/hosts/${host}/services`);
export const getRuns = () => get('/api/runs');
export const getRun = (id) => get(`/api/runs/${id}`);
export const postRun = (body) => post('/api/runs', body);
