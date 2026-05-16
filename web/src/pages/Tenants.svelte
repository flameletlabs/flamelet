<script>
  import { getTenantHosts } from '../lib/api.js'
  import { OS_COLORS } from '../lib/osColors.js'

  let { tenant = null } = $props()

  let selected = $state(null)
  let hosts = $state([])
  let selectedHost = $state(null)
  let groupBy = $state(sessionStorage.getItem('groupBy') || 'location')
  let collapseState = $state({})
  let copiedText = $state(null)
  let search = $state('')

  $effect(() => {
    if (!tenant) {
      selected = null
      hosts = []
      return
    }
    loadTenant()
  })

  async function loadTenant() {
    if (!tenant) return
    selected = { name: tenant }
    selectedHost = null
    hosts = await getTenantHosts(tenant)
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
    collapseState = { ...collapseState, [groupName]: !collapseState[groupName] }
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
    copiedText = text
    setTimeout(() => {
      copiedText = null
    }, 2000)
  }

  function osStripe(os) {
    if (!os) return '#666'
    const lower = os.toLowerCase()
    if (lower.includes('linux') || lower.includes('debian') || lower.includes('alpine') || lower.includes('ubuntu')) return OS_COLORS.Linux.color
    if (lower.includes('freebsd')) return OS_COLORS.FreeBSD.color
    if (lower.includes('openbsd')) return OS_COLORS.OpenBSD.color
    return '#666'
  }

  let grouped = $derived.by(() => {
    return groupHosts(hosts, groupBy)
  })

  let filtered = $derived.by(() => {
    if (!search) return grouped
    const s = search.toLowerCase()
    return Object.fromEntries(
      Object.entries(grouped)
        .map(([k, v]) => [k, v.filter(h =>
          h.name.toLowerCase().includes(s) ||
          (h.location || '').toLowerCase().includes(s) ||
          (h.os || '').toLowerCase().includes(s)
        )])
        .filter(([, v]) => v.length)
    )
  })
</script>

<div class="page">
  <div class="toolbar">
    <div class="toolbar-left">
      <span class="title">HOSTS</span>
      <span class="count">{hosts.length}</span>
    </div>

    <div class="group-tabs">
      <button class:active={groupBy === 'location'} onclick={() => setGroupBy('location')}>Location</button>
      <button class:active={groupBy === 'os'} onclick={() => setGroupBy('os')}>OS</button>
      <button class:active={groupBy === 'groups'} onclick={() => setGroupBy('groups')}>Groups</button>
      <button class:active={groupBy === 'none'} onclick={() => setGroupBy('none')}>All</button>
    </div>

    <input type="search" class="search" placeholder="filter hosts…" bind:value={search} />
  </div>

  <div class="hosts-content">
    {#if !selected}
      <div class="empty">No tenant selected</div>
    {:else if hosts.length === 0}
      <div class="empty">No hosts in this tenant</div>
    {:else if Object.keys(filtered).length === 0}
      <div class="empty">No hosts match your search</div>
    {:else}
      {#each Object.entries(filtered) as [groupName, groupHosts], groupIdx}
        <div class="group-block">
          <button class="group-header" onclick={() => toggleGroup(groupName)}>
            <span class="group-toggle" class:collapsed={collapseState[groupName]}>›</span>
            <span class="group-name">{groupName}</span>
            <span class="group-count">{groupHosts.length}</span>
          </button>

          {#if !collapseState[groupName]}
            {#each groupHosts as host, i}
              <button
                class="host-row"
                class:selected={selectedHost?.name === host.name}
                style="--os-stripe: {osStripe(host.os)}; animation-delay: {i * 30}ms"
                onclick={() => selectedHost = selectedHost?.name === host.name ? null : host}
              >
                <span class="row-stripe"></span>
                <span class="hostname">{host.name}</span>
                <span class="os-badge os-{host.os?.toLowerCase().replace(/\s+/g, '-')}">{host.os}</span>
                <span class="location">{host.location || '—'}</span>
                <span class="groups-cell">
                  {#each (host.groups || []).filter(g => !['linux','freebsd','openbsd'].includes(g.toLowerCase())).slice(0, 2) as g}
                    <span class="tag">{g}</span>
                  {/each}
                </span>
              </button>
            {/each}
          {/if}
        </div>
      {/each}
    {/if}
  </div>

  {#if selectedHost}
    <div class="host-sheet" style="--os-stripe: {osStripe(selectedHost.os)}">
      <div class="sheet-header">
        <span class="sheet-hostname">{selectedHost.name}</span>
        <span class="os-badge os-{selectedHost.os?.toLowerCase().replace(/\s+/g, '-')}">{selectedHost.os}</span>
        <button class="sheet-close" onclick={() => selectedHost = null} title="Close">✕</button>
      </div>
      <div class="sheet-body">
        <div class="sheet-row">
          <span class="sheet-key">Hostname</span>
          <div class="sheet-val-copy">
            <span class="mono">{selectedHost.name}</span>
            <button class="copy-btn" onclick={() => copyToClipboard(selectedHost.name)} title="Copy hostname">
              {copiedText === selectedHost.name ? '✓' : '⎘'}
            </button>
          </div>
        </div>
        {#if selectedHost.location}
          <div class="sheet-row">
            <span class="sheet-key">Location</span>
            <span>{selectedHost.location}</span>
          </div>
        {/if}
        {#if (selectedHost.groups || []).length}
          <div class="sheet-row">
            <span class="sheet-key">Groups</span>
            <div class="tag-list">
              {#each selectedHost.groups as g}
                <span class="tag">{g}</span>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg);
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    padding: 16px 28px;
    border-bottom: 1px solid var(--border);
    background: linear-gradient(90deg, var(--bg-2) 0%, rgba(15, 22, 41, 0.5) 100%);
  }

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .title {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .count {
    font-size: 12px;
    color: var(--text-muted);
    font-family: var(--mono);
  }

  .group-tabs {
    display: flex;
    gap: 4px;
    margin-left: auto;
  }

  .group-tabs button {
    min-height: 44px;
    padding: 8px 12px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text-muted);
    cursor: pointer;
    font-size: 11px;
    font-family: var(--ui);
    font-weight: 600;
    border-radius: 3px;
    transition: all 100ms;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .group-tabs button:hover {
    background: var(--bg);
    color: var(--text);
  }

  .group-tabs button.active {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--bg);
    font-weight: 700;
  }

  .search {
    min-height: 44px;
    padding: 10px 12px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--ui);
    font-size: 12px;
    border-radius: 3px;
    outline: none;
    width: 200px;
  }

  .search:focus {
    border-color: var(--accent);
  }

  .hosts-content {
    flex: 1;
    overflow-y: auto;
  }

  .empty {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-muted);
    font-size: 14px;
  }

  .group-block {
    border-bottom: 1px solid var(--border-muted);
  }

  .group-header {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 10px 16px;
    background: var(--bg-2);
    border: none;
    border-bottom: 1px solid var(--border-muted);
    cursor: pointer;
    min-height: 44px;
    position: sticky;
    top: 0;
    z-index: 10;
  }

  .group-header:hover {
    background: var(--bg-3);
  }

  .group-name {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: var(--text-dim);
    text-transform: uppercase;
    flex: 1;
  }

  .group-count {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--accent);
    font-weight: 600;
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

  .host-row {
    display: flex;
    align-items: center;
    gap: 0;
    width: 100%;
    background: none;
    border: none;
    border-bottom: 1px solid var(--border-muted);
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    color: inherit;
    padding: 0;
    min-height: 48px;
    transition: background 100ms;
    animation: rowIn 300ms ease-out forwards;
    opacity: 0;
  }

  @keyframes rowIn {
    from {
      opacity: 0;
      transform: translateX(-6px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  .host-row:hover {
    background: var(--bg-3);
  }

  .host-row.selected {
    background: rgba(0, 212, 170, 0.06);
  }

  .row-stripe {
    width: 4px;
    min-height: 48px;
    background: var(--os-stripe);
    flex-shrink: 0;
  }

  .hostname {
    font-family: var(--mono);
    font-weight: 700;
    color: var(--text);
    flex: 1;
    padding: 12px 16px;
    font-size: 13px;
  }

  .os-badge {
    padding: 2px 6px;
    border-radius: 2px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    flex-shrink: 0;
    margin-right: 8px;
  }

  .os-linux {
    background: rgba(68, 147, 248, 0.15);
    color: #4493f8;
  }

  .os-freebsd {
    background: rgba(205, 123, 106, 0.15);
    color: #cd7b6a;
  }

  .os-openbsd {
    background: rgba(227, 179, 65, 0.15);
    color: #e3b341;
  }

  .location {
    color: var(--text-dim);
    font-size: 12px;
    width: 120px;
    padding: 0 12px;
    flex-shrink: 0;
  }

  .groups-cell {
    display: flex;
    gap: 4px;
    padding: 0 12px;
    flex-shrink: 0;
  }

  .tag {
    font-family: var(--mono);
    font-size: 10px;
    padding: 2px 6px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 2px;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .host-sheet {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    max-height: 65vh;
    background: var(--bg-2);
    border-top: 1px solid var(--border);
    border-left: 4px solid var(--os-stripe);
    z-index: 50;
    overflow-y: auto;
    animation: sheetIn 250ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  @keyframes sheetIn {
    from {
      transform: translateY(100%);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  .sheet-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border-muted);
    position: sticky;
    top: 0;
    background: var(--bg-2);
    z-index: 1;
  }

  .sheet-hostname {
    font-family: var(--mono);
    font-weight: 700;
    font-size: 15px;
    color: var(--text);
    flex: 1;
  }

  .sheet-close {
    min-height: 44px;
    min-width: 44px;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 16px;
    transition: color 100ms;
  }

  .sheet-close:hover {
    color: var(--text);
  }

  .sheet-body {
    padding: 16px 24px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .sheet-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
  }

  .sheet-key {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    flex-shrink: 0;
    width: 80px;
  }

  .sheet-val-copy {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .mono {
    font-family: var(--mono);
    color: var(--text);
  }

  .copy-btn {
    min-height: 44px;
    min-width: 44px;
    background: none;
    border: 1px solid var(--border);
    color: var(--text-muted);
    cursor: pointer;
    font-size: 12px;
    border-radius: 3px;
    transition: all 100ms;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .copy-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
    background: rgba(0, 212, 170, 0.1);
  }

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  /* Responsive: 900px - hide groups column */
  @media (max-width: 900px) {
    .groups-cell {
      display: none;
    }
  }

  /* Responsive: 640px - hide location, compress toolbar */
  @media (max-width: 640px) {
    .toolbar {
      padding: 12px 16px;
    }

    .group-tabs {
      margin-left: 0;
      order: 3;
      width: 100%;
    }

    .search {
      width: 100%;
      order: 2;
    }

    .location {
      display: none;
    }

    .group-tabs button {
      flex: 1;
      padding: 8px 6px;
      font-size: 10px;
    }
  }

  /* Responsive: 360px - further compression */
  @media (max-width: 360px) {
    .hostname {
      font-size: 12px;
      padding: 10px 12px;
    }

    .row-stripe {
      width: 3px;
    }
  }
</style>
