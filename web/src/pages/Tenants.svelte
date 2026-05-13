<script>
  import { onMount } from 'svelte'
  import { getTenants, getTenantHosts } from '../lib/api.js'

  let tenants = $state([])
  let selected = $state(null)
  let hosts = $state([])
  let selectedHost = $state(null)

  onMount(async () => {
    tenants = await getTenants()
    if (tenants.length) selectTenant(tenants[0])
  })

  async function selectTenant(t) {
    selected = t
    selectedHost = null
    hosts = await getTenantHosts(t.name)
  }
</script>

<div class="layout">
  <aside>
    <div class="sidebar-header">TENANTS</div>
    {#each tenants as t}
      <button class="tenant-row" class:active={selected?.name === t.name} onclick={() => selectTenant(t)}>
        <span class="tenant-name">{t.name}</span>
        <span class="tenant-count">{t.host_count}</span>
      </button>
    {/each}
  </aside>

  <section class="panel">
    {#if selected}
      <div class="panel-header">
        <span class="mono">{selected.name}</span>
        <span class="path mono">{selected.path}</span>
      </div>
      <table>
        <thead>
          <tr>
            <th class="col-num">#</th>
            <th>HOSTNAME</th>
            <th>OS</th>
            <th>GROUPS</th>
          </tr>
        </thead>
        <tbody>
          {#each hosts as host, i}
            <tr class:selected={selectedHost?.name === host.name} onclick={() => selectedHost = host}>
              <td class="col-num mono">{(i+1).toString().padStart(2,'0')}</td>
              <td class="mono hostname">{host.name}</td>
              <td>
                <span class="badge badge-{host.os.toLowerCase()}">{host.os}</span>
              </td>
              <td class="groups">
                {#each host.groups as g}
                  <span class="tag">{g}</span>
                {/each}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>

      {#if selectedHost}
        <div class="inspector">
          <div class="inspector-header">
            <span>CONFIG · <span class="mono accent">{selectedHost.name}</span></span>
            <button onclick={() => selectedHost = null}>✕</button>
          </div>
          <div class="inspector-body">
            <p class="text-muted">← Select from the Operations catalog to inspect config</p>
          </div>
        </div>
      {/if}
    {:else}
      <div class="empty">No tenants configured</div>
    {/if}
  </section>
</div>

<style>
  .layout {
    display: grid;
    grid-template-columns: 200px 1fr;
    height: 100%;
  }

  aside {
    border-right: 1px solid var(--border);
    background: var(--bg-2);
    overflow-y: auto;
  }

  .sidebar-header {
    padding: 12px 16px 8px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
    border-bottom: 1px solid var(--border-muted);
  }

  .tenant-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 10px 16px;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    text-align: left;
    border-bottom: 1px solid var(--border-muted);
    transition: background 0.1s, color 0.1s;
  }

  .tenant-row:hover {
    background: var(--bg-3);
    color: var(--text);
  }

  .tenant-row.active {
    background: var(--accent-bg);
    color: var(--accent);
  }

  .tenant-name {
    font-family: var(--mono);
    font-size: 12px;
  }

  .tenant-count {
    font-family: var(--mono);
    font-size: 11px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 2px;
    padding: 1px 5px;
    color: var(--text-dim);
  }

  .panel {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .panel-header {
    display: flex;
    align-items: baseline;
    gap: 16px;
    padding: 14px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-2);
  }

  .panel-header .mono {
    font-size: 13px;
    font-weight: 700;
    color: var(--text);
  }

  .path {
    font-size: 11px;
    color: var(--text-dim);
  }

  table {
    width: 100%;
    border-collapse: collapse;
    overflow-y: auto;
  }

  thead tr {
    border-bottom: 1px solid var(--border);
  }

  th {
    text-align: left;
    padding: 10px 16px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
    background: var(--bg-2);
    position: sticky;
    top: 0;
  }

  td {
    padding: 10px 16px;
    border-bottom: 1px solid var(--border-muted);
  }

  tr:hover td {
    background: var(--bg-2);
    cursor: pointer;
  }

  tr.selected td {
    background: var(--accent-bg);
  }

  .col-num {
    width: 44px;
    color: var(--text-dim);
    font-size: 11px;
  }

  .hostname {
    font-size: 13px;
    color: var(--text);
  }

  .groups {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .tag {
    font-family: var(--mono);
    font-size: 10px;
    padding: 1px 6px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 2px;
    color: var(--text-muted);
  }

  .inspector {
    border-top: 1px solid var(--border);
    background: var(--bg-2);
    max-height: 260px;
    overflow-y: auto;
  }

  .inspector-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 24px;
    border-bottom: 1px solid var(--border);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-muted);
  }

  .inspector-header button {
    background: none;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    font-size: 13px;
    padding: 2px 6px;
  }

  .inspector-body {
    padding: 16px 24px;
  }

  .accent {
    color: var(--accent);
  }

  .text-muted {
    color: var(--text-muted);
    font-size: 12px;
  }

  .empty {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-dim);
  }
</style>
