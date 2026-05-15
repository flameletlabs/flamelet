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
      <button class="tenant-row" class:active={selected?.name === t.name} onclick={() => selectTenant(t)} style="animation-delay: {tenants.indexOf(t) * 50}ms;">
        <span class="tenant-name">{t.name}</span>
        <span class="tenant-count">{t.host_count}</span>
      </button>
    {/each}
  </aside>

  <section class="panel">
    {#if selected}
      <div class="panel-header">
        <div class="header-content">
          <div class="tenant-title">{selected.name}</div>
          <div class="tenant-path mono">{selected.path}</div>
        </div>
      </div>

      <div class="group-selector">
        <span class="group-label">Group by:</span>
        <div class="btn-group">
          <button class="group-btn" class:active={groupBy === 'location'} on:click={() => setGroupBy('location')}>Location</button>
          <button class="group-btn" class:active={groupBy === 'os'} on:click={() => setGroupBy('os')}>OS</button>
          <button class="group-btn" class:active={groupBy === 'groups'} on:click={() => setGroupBy('groups')}>Groups</button>
          <button class="group-btn" class:active={groupBy === 'none'} on:click={() => setGroupBy('none')}>None</button>
        </div>
      </div>

      <!-- Desktop Table View -->
      <div class="table-view">
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
      </div>

      <!-- Mobile Card View -->
      <div class="cards-view">
        {#each Object.entries(grouped) as [groupName, groupHosts], groupIdx}
          <div class="group-section">
            <div class="group-title" on:click={() => toggleGroup(groupName)}>
              <span class="group-toggle" class:collapsed={collapseState[groupName]}>›</span>
              <span>{groupName}</span>
              <span class="group-count-badge">{groupHosts.length}</span>
            </div>
            {#if !collapseState[groupName]}
              <div class="hosts-cards">
                {#each groupHosts as host, i (host.name)}
                  <div class="host-card" class:selected={selectedHost?.name === host.name} on:click={() => selectedHost = host} style="animation-delay: {(groupIdx * 10 + i) * 40}ms;">
                    <div class="card-header">
                      <div class="host-name">{host.name}</div>
                      <span class="badge badge-{host.os.toLowerCase()}">{host.os}</span>
                    </div>
                    {#if host.location}
                      <div class="card-meta">📍 {host.location}</div>
                    {/if}
                    {#if host.groups.filter(g => !['linux','freebsd','openbsd'].includes(g.toLowerCase())).length > 0}
                      <div class="card-tags">
                        {#each host.groups.filter(g => !['linux','freebsd','openbsd'].includes(g.toLowerCase())).slice(0, 3) as g}
                          <span class="tag">{g}</span>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      </div>

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
    padding: 12px 14px;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    text-align: left;
    border-bottom: 1px solid var(--border-muted);
    transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
    min-height: 44px;
  }

  .tenant-row:hover {
    background: var(--bg-3);
    color: var(--text);
  }

  .tenant-row:active {
    background: rgba(0, 212, 170, 0.1);
  }

  .tenant-row.active {
    background: var(--accent-bg);
    color: var(--accent);
    border-left: 3px solid var(--accent);
    padding-left: 11px;
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
    flex-direction: column;
    gap: 8px;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-2);
  }

  .header-content {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .tenant-title {
    font-family: var(--ui);
    font-size: clamp(18px, 5vw, 24px);
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.5px;
  }

  .tenant-path {
    font-size: clamp(11px, 2vw, 12px);
    color: var(--text-muted);
    letter-spacing: 0.5px;
  }

  .table-view {
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow-y: auto;
  }

  .cards-view {
    display: none;
    flex-direction: column;
    flex: 1;
    overflow-y: auto;
    gap: 12px;
    padding: 14px 12px;
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
    background: var(--bg-3);
    cursor: pointer;
  }

  tr:active td {
    background: rgba(0, 212, 170, 0.05);
  }

  tr.selected td {
    background: var(--accent-bg);
    border-left: 3px solid var(--accent);
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
    gap: 12px;
    padding: 12px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-2);
    flex-wrap: wrap;
  }

  .group-label {
    font-size: clamp(10px, 1.5vw, 11px);
    font-weight: 600;
    text-transform: uppercase;
    color: var(--text-dim);
    letter-spacing: 0.04em;
    line-height: 1.4;
  }

  .btn-group {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .group-btn {
    padding: 8px 12px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text-muted);
    cursor: pointer;
    font-size: 12px;
    font-family: var(--ui);
    font-weight: 600;
    border-radius: 6px;
    transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
    line-height: 1.4;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    min-height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .group-btn:hover {
    background: var(--bg);
    color: var(--text);
    border-color: var(--text-muted);
  }

  .group-btn:active {
    background: rgba(0, 212, 170, 0.1);
    color: var(--accent);
  }

  .group-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--bg);
    font-weight: 700;
    box-shadow: 0 2px 8px rgba(0, 212, 170, 0.2);
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

  .group-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .group-title {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 14px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 6px;
    cursor: pointer;
    user-select: none;
    font-weight: 600;
    font-size: clamp(14px, 3vw, 15px);
    color: var(--text);
    transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  .group-title:hover {
    background: var(--bg);
    border-color: var(--text-muted);
  }

  .group-title .group-toggle {
    display: inline-block;
    transform: rotate(90deg);
    transition: transform 150ms;
    font-size: 14px;
    color: var(--text-muted);
  }

  .group-title .group-toggle.collapsed {
    transform: rotate(0deg);
  }

  .group-count-badge {
    margin-left: auto;
    background: var(--accent);
    color: var(--bg);
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 12px;
    font-weight: 600;
    font-family: var(--mono);
  }

  .hosts-cards {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .host-card {
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
    cursor: pointer;
    transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
    animation: slideIn 300ms ease-out forwards;
    opacity: 0;
    min-height: 44px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .host-card:hover {
    background: var(--bg-3);
    border-color: rgba(0, 212, 170, 0.3);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }

  .host-card:active {
    background: rgba(0, 212, 170, 0.1);
  }

  .host-card.selected {
    background: var(--accent-bg);
    border-color: var(--accent);
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    justify-content: space-between;
  }

  .host-name {
    font-family: var(--ui);
    font-size: clamp(15px, 3.5vw, 16px);
    font-weight: 700;
    color: var(--text);
    flex: 1;
  }

  .card-meta {
    font-size: clamp(13px, 2.5vw, 14px);
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .card-tags {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .card-tags .tag {
    font-size: clamp(11px, 2vw, 12px);
    padding: 4px 8px;
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

    .table-view {
      display: none;
    }

    .cards-view {
      display: flex;
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

    .group-selector {
      flex-wrap: wrap;
      gap: 6px;
      padding: 10px 12px;
    }

    .group-label {
      font-size: clamp(11px, 2vw, 12px);
      width: 100%;
    }

    .btn-group {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      width: 100%;
    }

    .group-btn {
      flex: 1;
      min-width: 70px;
      padding: 8px 10px;
      font-size: clamp(11px, 2vw, 12px);
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
      min-height: 40px;
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
      padding: 12px 16px;
    }

    .tenant-title {
      font-size: clamp(16px, 4.5vw, 20px);
    }

    .tenant-path {
      font-size: clamp(10px, 1.8vw, 11px);
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
      padding: 8px 12px;
      gap: 4px;
      flex-wrap: wrap;
    }

    .group-label {
      font-size: 9px;
      width: 100%;
    }

    .group-btn {
      padding: 6px 8px;
      font-size: 10px;
      flex: 1;
      min-width: 60px;
    }

    .host-card {
      padding: 12px;
      gap: 8px;
    }

    .host-name {
      font-size: clamp(14px, 3.2vw, 15px);
    }

    .card-meta {
      font-size: clamp(12px, 2.2vw, 13px);
    }

    .card-tags .tag {
      font-size: clamp(10px, 1.8vw, 11px);
      padding: 3px 6px;
    }

    .group-title {
      font-size: clamp(13px, 2.8vw, 14px);
      padding: 10px 12px;
    }

    .cards-view {
      padding: 10px 8px;
      gap: 8px;
    }
  }
</style>
