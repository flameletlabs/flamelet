<script>
  import { onMount } from 'svelte'
  import { getTenants, getTenantHosts } from '../lib/api.js'

  let tenants = []
  let selected = null
  let hosts = []
  let selectedHost = null
  let groupBy = sessionStorage.getItem('groupBy') || 'location'
  let collapseState = {}

  onMount(async () => {
    tenants = await getTenants()
    if (tenants.length) selectTenant(tenants[0])
  })

  async function selectTenant(t) {
    selected = t
    selectedHost = null
    hosts = await getTenantHosts(t.name)
    collapseState = {}
  }

  function setGroupBy(method) {
    groupBy = method
    sessionStorage.setItem('groupBy', method)
    collapseState = {}
  }

  function groupHosts(hostList, method) {
    const grouped = {}

    hostList.forEach(h => {
      let groupKey
      if (method === 'os') {
        groupKey = h.os || 'Unknown'
      } else if (method === 'groups') {
        const primaryGroup = h.groups.find(g => !['linux','freebsd','openbsd'].includes(g.toLowerCase())) || '(no group)'
        groupKey = primaryGroup
      } else if (method === 'none') {
        groupKey = 'All Hosts'
      } else {
        groupKey = h.location || '(no location)'
      }

      if (!grouped[groupKey]) grouped[groupKey] = []
      grouped[groupKey].push(h)
    })

    return Object.keys(grouped).sort().reduce((acc, key) => {
      acc[key] = grouped[key]
      return acc
    }, {})
  }

  function toggleGroup(groupName) {
    collapseState[groupName] = !collapseState[groupName]
  }

  $: grouped = groupHosts(hosts, groupBy)
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

      <div class="group-selector">
        <span class="group-label">Group by:</span>
        <button class="group-btn" class:active={groupBy === 'location'} on:click={() => setGroupBy('location')}>Location</button>
        <button class="group-btn" class:active={groupBy === 'os'} on:click={() => setGroupBy('os')}>OS</button>
        <button class="group-btn" class:active={groupBy === 'groups'} on:click={() => setGroupBy('groups')}>Groups</button>
        <button class="group-btn" class:active={groupBy === 'none'} on:click={() => setGroupBy('none')}>None</button>
      </div>

      <table>
        <thead>
          <tr>
            <th class="col-num">#</th>
            <th>HOSTNAME</th>
            <th>OS</th>
            <th>LOCATION</th>
            <th>GROUPS</th>
          </tr>
        </thead>
        <tbody>
          {#each Object.entries(grouped) as [groupName, groupHosts]}
            <tr class="group-header" on:click={() => toggleGroup(groupName)}>
              <td colspan="5">
                <div class="group-header-inner">
                  <span class="group-toggle" class:collapsed={collapseState[groupName]}>›</span>
                  <span class="group-name">{groupName}</span>
                  <span class="group-count">{groupHosts.length} host{groupHosts.length !== 1 ? 's' : ''}</span>
                </div>
              </td>
            </tr>

            {#each groupHosts as host, i}
              <tr
                class="host-row"
                class:collapsed={collapseState[groupName]}
                class:selected={selectedHost?.name === host.name}
                on:click={() => selectedHost = host}
              >
                <td class="col-num mono">{String(i+1).padStart(2,'0')}</td>
                <td class="mono hostname">{host.name}</td>
                <td class="col-os">
                  <span class="badge badge-{host.os.toLowerCase()}">{host.os}</span>
                </td>
                <td class="col-location" style="color:var(--text-muted);">{host.location || '—'}</td>
                <td class="groups">
                  {#each host.groups.filter(g => !['linux','freebsd','openbsd'].includes(g.toLowerCase())).slice(0, 2) as g}
                    <span class="tag">{g}</span>
                  {/each}
                  {#if host.groups.filter(g => !['linux','freebsd','openbsd'].includes(g.toLowerCase())).length > 2}
                    <span class="tag-more">+{host.groups.filter(g => !['linux','freebsd','openbsd'].includes(g.toLowerCase())).length - 2}</span>
                  {/if}
                </td>
              </tr>
            {/each}
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
    font-size: clamp(12px, 1.8vw, 13px);
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.3px;
  }

  .path {
    font-size: clamp(10px, 1.5vw, 11px);
    color: var(--text-dim);
    letter-spacing: -0.1px;
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
    padding: clamp(8px, 1.2vw, 10px) clamp(12px, 1.8vw, 16px);
    font-size: clamp(9px, 1.4vw, 10px);
    font-weight: 600;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    text-transform: uppercase;
    background: var(--bg-2);
    position: sticky;
    top: 0;
    line-height: 1.4;
  }

  td {
    padding: clamp(8px, 1.2vw, 10px) clamp(12px, 1.8vw, 16px);
    border-bottom: 1px solid var(--border-muted);
    line-height: 1.5;
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

  .group-selector {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-2);
  }

  .group-label {
    font-size: clamp(10px, 1.5vw, 11px);
    font-weight: 600;
    text-transform: uppercase;
    color: var(--text-dim);
    letter-spacing: 0.04em;
    line-height: 1.4;
  }

  .group-btn {
    padding: clamp(4px, 0.8vw, 5px) clamp(8px, 1.2vw, 10px);
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text-muted);
    cursor: pointer;
    font-size: clamp(10px, 1.5vw, 11px);
    font-family: var(--mono);
    font-weight: 500;
    border-radius: 2px;
    transition: all 150ms;
    line-height: 1.4;
  }

  .group-btn:hover {
    background: var(--bg);
    color: var(--text);
  }

  .group-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--bg);
    font-weight: 600;
  }

  .group-header {
    background: var(--bg-2);
    cursor: pointer;
    user-select: none;
  }

  .group-header:hover {
    background: var(--bg-3);
  }

  .group-header-inner {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .group-toggle {
    display: inline-block;
    transform: rotate(90deg);
    transition: transform 150ms;
    color: var(--text-muted);
    font-size: 14px;
  }

  .group-toggle.collapsed {
    transform: rotate(0deg);
  }

  .group-name {
    font-weight: 600;
    color: var(--text);
    flex: 1;
  }

  .group-count {
    font-size: 11px;
    color: var(--text-muted);
  }

  .host-row.collapsed {
    display: none;
  }

  .col-location {
    width: 120px;
  }

  .col-os {
    width: 80px;
    text-align: center;
  }

  .tag-more {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--text-dim);
  }

  @media (max-width: 768px) {
    .layout {
      grid-template-columns: 1fr;
    }

    aside {
      border-right: none;
      border-bottom: 1px solid var(--border);
      max-height: 140px;
      overflow-y: auto;
    }

    .panel {
      min-height: 0;
    }

    th {
      font-size: 9px;
      padding: 8px 12px;
    }

    td {
      padding: 8px 12px;
      font-size: 12px;
    }

    .col-num {
      width: 32px;
    }

    .col-location {
      display: none;
    }

    .groups {
      display: none;
    }
  }

  @media (max-width: 640px) {
    aside {
      max-height: 100px;
    }

    .sidebar-header {
      padding: 8px 12px 6px;
      font-size: 9px;
    }

    .tenant-row {
      padding: 8px 12px;
      font-size: 11px;
    }

    .tenant-name {
      font-size: 11px;
    }

    .tenant-count {
      font-size: 9px;
      padding: 0px 3px;
    }

    .panel-header {
      flex-direction: column;
      gap: 6px;
      padding: 10px 16px;
    }

    .panel-header .mono {
      font-size: 12px;
    }

    .path {
      font-size: 10px;
    }

    table {
      font-size: 12px;
    }

    th {
      font-size: 8px;
      padding: 6px 8px;
    }

    td {
      padding: 6px 8px;
    }

    .hostname {
      font-size: 11px;
    }

    .group-selector {
      padding: 8px 16px;
      gap: 4px;
      flex-wrap: wrap;
    }

    .group-label {
      font-size: 10px;
    }

    .group-btn {
      padding: 4px 8px;
      font-size: 10px;
    }
  }
</style>
