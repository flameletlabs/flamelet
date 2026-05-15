<script>
  import { onMount, tick } from 'svelte'
  import { getTenants, getTenantHosts, postRun } from '../lib/api.js'

  let tenants = $state([])
  let hosts = $state([])
  let tasks = [
    'users', 'sudo', 'packages', 'sysctl', 'services', 'wireguard', 'monit',
    'unbound', 'pf', 'docker', 'node_exporter', 'k3s', 'bhyve', 'jails',
    'storage', 'nginx', 'postgresql', 'prometheus', 'registry', 'autossh',
    'opensmtpd', 'all'
  ]

  let selectedTenant = $state('')
  let selectedTask = $state('sysctl')
  let selectedHosts = $state(new Set())
  let dryRun = $state(true)
  let diff = $state(false)

  let runId = $state(null)
  let running = $state(false)
  let status = $state(null)
  let logLines = $state([])
  let logEl = $state(null)

  // Host selection state
  let groupBy = $state('location')
  let hostSearch = $state('')
  let collapsedGroups = $state(new Set())

  onMount(async () => {
    tenants = await getTenants()
    if (tenants.length) {
      selectedTenant = tenants[0].name
      await loadHosts()
    }
  })

  async function loadHosts() {
    hosts = await getTenantHosts(selectedTenant)
    selectedHosts = new Set()
    collapsedGroups = new Set()
  }

  // OS-family groups to exclude from "group" view (they're redundant with OS grouping)
  const OS_GROUPS = new Set(['openbsd', 'freebsd', 'linux', 'debian', 'alpine'])

  let groupedHosts = $derived.by(() => {
    const q = hostSearch.toLowerCase()
    const filtered = q
      ? hosts.filter(h => h.name.toLowerCase().includes(q) || h.os.toLowerCase().includes(q) || h.location?.toLowerCase().includes(q))
      : hosts

    const groups = {}
    for (const h of filtered) {
      let keys = []
      if (groupBy === 'location') {
        keys = [h.location || 'unknown']
      } else if (groupBy === 'os') {
        keys = [h.os || 'unknown']
      } else {
        // meaningful groups: exclude OS-family and location names
        keys = (h.groups || []).filter(g => !OS_GROUPS.has(g.toLowerCase()) && g !== h.location)
        if (keys.length === 0) keys = ['ungrouped']
      }
      for (const k of keys) {
        if (!groups[k]) groups[k] = []
        if (!groups[k].find(x => x.name === h.name)) groups[k].push(h)
      }
    }
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
  })

  function groupSelectionState(groupHosts) {
    const sel = groupHosts.filter(h => selectedHosts.has(h.name)).length
    if (sel === 0) return 'none'
    if (sel === groupHosts.length) return 'all'
    return 'partial'
  }

  function toggleGroup(groupHosts) {
    const state = groupSelectionState(groupHosts)
    const next = new Set(selectedHosts)
    if (state === 'all') {
      groupHosts.forEach(h => next.delete(h.name))
    } else {
      groupHosts.forEach(h => next.add(h.name))
    }
    selectedHosts = next
  }

  function toggleHost(name) {
    const next = new Set(selectedHosts)
    next.has(name) ? next.delete(name) : next.add(name)
    selectedHosts = next
  }

  function toggleCollapseGroup(key) {
    const next = new Set(collapsedGroups)
    next.has(key) ? next.delete(key) : next.add(key)
    collapsedGroups = next
  }

  function selectAll() {
    selectedHosts = new Set(hosts.map(h => h.name))
  }

  function selectNone() {
    selectedHosts = new Set()
  }

  const OS_COLORS = {
    openbsd: '#e3b341',
    freebsd: '#cd7b6a',
    linux: '#4493f8',
    unknown: '#666',
  }

  function osColor(os) {
    return OS_COLORS[os?.toLowerCase()] || OS_COLORS.unknown
  }

  async function startRun() {
    running = true
    logLines = []
    status = null
    const res = await postRun({
      tenant: selectedTenant,
      task: selectedTask,
      hosts: [...selectedHosts],
      dry_run: dryRun,
      diff,
    })
    runId = res.run_id
    streamLogs(runId)
  }

  function lineClass(text) {
    if (text.startsWith('[CHANGED]')) return 'log-changed'
    if (text.startsWith('[OK]')) return 'log-ok'
    if (text.startsWith('[FAILED]')) return 'log-failed'
    if (text.startsWith('[CHECK]')) return 'log-check'
    if (text.startsWith('→ ')) return 'log-op'
    if (text.startsWith('=== Summary') || text.startsWith('=== Deployment')) return 'log-summary'
    return ''
  }

  function streamLogs(id) {
    const es = new EventSource(`/api/runs/${id}/stream`)
    es.onmessage = async (e) => {
      const now = new Date()
      const ts = now.toTimeString().slice(0, 8)
      logLines = [...logLines, { ts, text: e.data }]
      await tick()
      logEl?.scrollTo({ top: logEl.scrollHeight, behavior: 'smooth' })
    }
    es.onerror = () => {
      es.close()
      running = false
    }
  }
</script>

<div class="layout">
  <aside>
    <div class="form-header">
      <span>EXECUTE</span>
      {#if selectedHosts.size > 0}
        <span class="sel-count">{selectedHosts.size} host{selectedHosts.size !== 1 ? 's' : ''}</span>
      {/if}
    </div>

    <div class="form-body">
      <!-- Tenant + Task -->
      <div class="field-row">
        <label class="field">
          <span class="field-label">TENANT</span>
          <select bind:value={selectedTenant} onchange={loadHosts}>
            {#each tenants as t}
              <option value={t.name}>{t.name}</option>
            {/each}
          </select>
        </label>
        <label class="field">
          <span class="field-label">TASK</span>
          <select bind:value={selectedTask}>
            {#each tasks as t}
              <option value={t}>{t}</option>
            {/each}
          </select>
        </label>
      </div>

      <!-- Host selector -->
      <div class="host-panel">
        <div class="host-toolbar">
          <div class="group-tabs">
            <button class:active={groupBy === 'location'} onclick={() => groupBy = 'location'}>Location</button>
            <button class:active={groupBy === 'os'} onclick={() => groupBy = 'os'}>OS</button>
            <button class:active={groupBy === 'group'} onclick={() => groupBy = 'group'}>Group</button>
          </div>
          <div class="host-actions">
            <button class="txt-btn" onclick={selectAll}>all</button>
            <span class="sep">·</span>
            <button class="txt-btn" onclick={selectNone}>none</button>
          </div>
        </div>

        <div class="host-search-wrap">
          <span class="search-icon">⌕</span>
          <input
            type="search"
            placeholder="filter hosts…"
            bind:value={hostSearch}
            class="host-search"
          />
        </div>

        <div class="host-list">
          {#each groupedHosts as [groupKey, groupHosts]}
            {@const selState = groupSelectionState(groupHosts)}
            {@const collapsed = collapsedGroups.has(groupKey)}
            {@const selCount = groupHosts.filter(h => selectedHosts.has(h.name)).length}

            <div class="group-block">
              <div
                class="group-header"
                role="button"
                tabindex="0"
                onclick={() => toggleCollapseGroup(groupKey)}
                onkeydown={e => (e.key === 'Enter' || e.key === ' ') && toggleCollapseGroup(groupKey)}
              >
                <button
                  class="group-check"
                  class:sel-all={selState === 'all'}
                  class:sel-partial={selState === 'partial'}
                  onclick={(e) => { e.stopPropagation(); toggleGroup(groupHosts) }}
                  title="Select group"
                  aria-label="Toggle group {groupKey}"
                ></button>
                <span class="group-name">{groupKey}</span>
                <span class="group-meta">
                  {#if selCount > 0}
                    <span class="group-sel">{selCount}/</span>
                  {/if}
                  {groupHosts.length}
                </span>
                <span class="chevron" class:collapsed>{collapsed ? '›' : '›'}</span>
              </div>

              {#if !collapsed}
                <div class="group-hosts">
                  {#each groupHosts as h}
                    {@const selected = selectedHosts.has(h.name)}
                    <button
                      class="host-chip"
                      class:selected
                      onclick={() => toggleHost(h.name)}
                      title="{h.name} · {h.os} · {h.location}"
                    >
                      <span class="os-dot" style="background:{osColor(h.os)}"></span>
                      <span class="host-chip-name">{h.name}</span>
                      {#if selected}
                        <span class="chip-check">✓</span>
                      {/if}
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          {/each}

          {#if groupedHosts.length === 0}
            <div class="empty">no hosts match</div>
          {/if}
        </div>
      </div>

      <!-- Options -->
      <div class="options-row">
        <label class="toggle-label">
          <span class="toggle-switch" class:on={dryRun}>
            <input type="checkbox" bind:checked={dryRun} />
          </span>
          <span class="toggle-text">Check mode</span>
        </label>
        <label class="toggle-label">
          <span class="toggle-switch" class:on={diff}>
            <input type="checkbox" bind:checked={diff} />
          </span>
          <span class="toggle-text">Show diffs</span>
        </label>
      </div>

      <button
        class="run-btn"
        onclick={startRun}
        disabled={running || !selectedHosts.size}
      >
        {#if running}
          <span class="spin">◌</span> RUNNING
        {:else}
          <span>▶</span> RUN{dryRun ? ' CHECK' : ''}
        {/if}
      </button>
    </div>
  </aside>

  <section class="terminal-panel">
    <div class="terminal-header">
      <div class="term-left">
        <span class="term-title">OUTPUT</span>
        {#if runId}
          <span class="run-id mono">#{runId}</span>
        {/if}
      </div>
      <div class="term-right">
        {#if running}
          <span class="live-badge">● LIVE</span>
        {:else if logLines.length > 0}
          <span class="line-count">{logLines.length} lines</span>
        {/if}
      </div>
    </div>
    <div class="terminal" bind:this={logEl}>
      {#if logLines.length === 0 && !running}
        <span class="prompt">$ flamelet --task {selectedTask}{dryRun ? ' --dry' : ''}{diff ? ' --diff' : ''}</span>
      {/if}
      {#each logLines as line}
        <div class="log-line">
          <span class="ts">[{line.ts}]</span>
          <span class="text {lineClass(line.text)}">{line.text}</span>
        </div>
      {/each}
      {#if running}
        <div class="cursor">_</div>
      {/if}
    </div>
  </section>
</div>

<style>
  .layout {
    display: grid;
    grid-template-columns: 300px 1fr;
    height: 100%;
    overflow: hidden;
  }

  aside {
    border-right: 1px solid var(--border);
    background: var(--bg-2);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .form-header {
    padding: 14px 20px 12px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--text-dim);
    text-transform: uppercase;
    border-bottom: 1px solid var(--border-muted);
    background: linear-gradient(90deg, var(--bg-2) 0%, rgba(15, 22, 41, 0.5) 100%);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }

  .sel-count {
    font-size: 10px;
    color: var(--accent);
    font-family: var(--mono);
    font-weight: 700;
  }

  .form-body {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    flex: 1;
    overflow: hidden;
  }

  /* Tenant + Task side by side */
  .field-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .field-label {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  select {
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--ui);
    font-size: 12px;
    font-weight: 500;
    padding: 7px 8px;
    border-radius: 4px;
    cursor: pointer;
    outline: none;
    transition: border-color 150ms;
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
  }

  select:focus {
    border-color: var(--accent);
  }

  /* Host panel — takes remaining space */
  .host-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0;
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
    min-height: 0;
  }

  .host-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 8px;
    border-bottom: 1px solid var(--border-muted);
    background: var(--bg-3);
    flex-shrink: 0;
  }

  .group-tabs {
    display: flex;
    gap: 2px;
  }

  .group-tabs button {
    background: none;
    border: none;
    font-family: var(--ui);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--text-dim);
    cursor: pointer;
    padding: 3px 8px;
    border-radius: 3px;
    transition: all 100ms;
  }

  .group-tabs button:hover {
    color: var(--text-muted);
    background: var(--bg-2);
  }

  .group-tabs button.active {
    color: var(--accent);
    background: rgba(0, 212, 170, 0.08);
  }

  .host-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .txt-btn {
    background: none;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    font-family: var(--mono);
    font-size: 10px;
    padding: 2px 4px;
    transition: color 100ms;
  }

  .txt-btn:hover {
    color: var(--accent);
  }

  .sep {
    color: var(--border);
    font-size: 10px;
  }

  .host-search-wrap {
    position: relative;
    flex-shrink: 0;
    border-bottom: 1px solid var(--border-muted);
  }

  .search-icon {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-dim);
    font-size: 14px;
    pointer-events: none;
    line-height: 1;
  }

  .host-search {
    width: 100%;
    background: var(--bg-2);
    border: none;
    color: var(--text);
    font-family: var(--mono);
    font-size: 11px;
    padding: 7px 10px 7px 28px;
    outline: none;
    box-sizing: border-box;
  }

  .host-search::placeholder {
    color: var(--text-dim);
  }

  /* Scrollable host list */
  .host-list {
    flex: 1;
    overflow-y: auto;
    padding: 4px 0;
  }

  .group-block {
    border-bottom: 1px solid var(--border-muted);
  }

  .group-block:last-child {
    border-bottom: none;
  }

  .group-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 8px 5px 6px;
    cursor: pointer;
    user-select: none;
    transition: background 100ms;
  }

  .group-header:hover {
    background: var(--bg-3);
  }

  /* Custom group checkbox button */
  .group-check {
    width: 14px;
    height: 14px;
    border: 1.5px solid var(--border);
    background: transparent;
    border-radius: 3px;
    cursor: pointer;
    flex-shrink: 0;
    position: relative;
    transition: all 100ms;
    padding: 0;
  }

  .group-check:hover {
    border-color: var(--accent);
  }

  .group-check.sel-all {
    background: var(--accent);
    border-color: var(--accent);
  }

  .group-check.sel-all::after {
    content: '';
    position: absolute;
    inset: 2px;
    background: var(--bg);
    clip-path: polygon(20% 50%, 40% 70%, 80% 20%, 90% 30%, 40% 85%, 10% 60%);
  }

  .group-check.sel-partial {
    border-color: var(--accent);
  }

  .group-check.sel-partial::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 2px;
    right: 2px;
    height: 1.5px;
    background: var(--accent);
    transform: translateY(-50%);
  }

  .group-name {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 600;
    color: var(--text);
    text-transform: lowercase;
    flex: 1;
  }

  .group-meta {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--text-dim);
  }

  .group-sel {
    color: var(--accent);
  }

  .chevron {
    font-size: 12px;
    color: var(--text-dim);
    transition: transform 150ms;
    line-height: 1;
    transform: rotate(90deg);
  }

  .chevron.collapsed {
    transform: rotate(0deg);
  }

  /* Host chips inside groups */
  .group-hosts {
    padding: 2px 6px 6px 28px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .host-chip {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 4px 8px 4px 6px;
    border-radius: 3px;
    border: 1px solid transparent;
    background: transparent;
    cursor: pointer;
    text-align: left;
    width: 100%;
    transition: all 100ms;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text-muted);
  }

  .host-chip:hover {
    background: var(--bg-3);
    border-color: var(--border-muted);
    color: var(--text);
  }

  .host-chip.selected {
    background: rgba(0, 212, 170, 0.06);
    border-color: rgba(0, 212, 170, 0.2);
    color: var(--text);
  }

  .os-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
    opacity: 0.85;
  }

  .host-chip-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chip-check {
    font-size: 9px;
    color: var(--accent);
    flex-shrink: 0;
  }

  .empty {
    padding: 16px;
    text-align: center;
    color: var(--text-dim);
    font-size: 11px;
    font-family: var(--mono);
  }

  /* Options row */
  .options-row {
    display: flex;
    gap: 16px;
    flex-shrink: 0;
  }

  .toggle-label {
    display: flex;
    align-items: center;
    gap: 7px;
    cursor: pointer;
  }

  .toggle-switch {
    position: relative;
    width: 28px;
    height: 15px;
    border-radius: 8px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    transition: all 150ms;
    flex-shrink: 0;
  }

  .toggle-switch.on {
    background: rgba(0, 212, 170, 0.2);
    border-color: var(--accent);
  }

  .toggle-switch::after {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--text-dim);
    transition: all 150ms;
  }

  .toggle-switch.on::after {
    left: 15px;
    background: var(--accent);
  }

  .toggle-switch input {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-text {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--ui);
    white-space: nowrap;
  }

  /* Run button */
  .run-btn {
    padding: 11px 16px;
    background: var(--accent);
    border: none;
    color: var(--bg);
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    cursor: pointer;
    border-radius: 4px;
    transition: all 150ms;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .run-btn:hover:not(:disabled) {
    background: #00c99f;
    box-shadow: 0 2px 8px rgba(0, 212, 170, 0.3);
  }

  .run-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .spin {
    display: inline-block;
    animation: spin 1.2s linear infinite;
  }

  /* Terminal */
  .terminal-panel {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .terminal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    border-bottom: 1px solid var(--border);
    background: linear-gradient(90deg, var(--bg-2) 0%, rgba(15, 22, 41, 0.5) 100%);
    flex-shrink: 0;
  }

  .term-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .term-title {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .run-id {
    font-size: 10px;
    color: var(--text-dim);
    opacity: 0.6;
  }

  .term-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .live-badge {
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    color: var(--running);
    letter-spacing: 0.08em;
    animation: pulse 1.2s ease-in-out infinite;
  }

  .line-count {
    font-family: var(--mono);
    font-size: 10px;
    color: var(--text-dim);
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .terminal {
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px;
    font-family: var(--mono);
    font-size: clamp(11px, 2.2vw, 12px);
    line-height: 1.7;
    background: var(--bg);
    background-image: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 27px,
      rgba(255, 255, 255, 0.012) 27px,
      rgba(255, 255, 255, 0.012) 28px
    );
  }

  .prompt { color: var(--text-dim); }

  .log-line {
    display: flex;
    gap: 12px;
  }

  .ts {
    color: var(--text-dim);
    min-width: 80px;
    flex-shrink: 0;
  }

  .text {
    color: var(--text-muted);
    word-break: break-all;
  }

  .text.log-changed { color: #f0883e; font-weight: 600; }
  .text.log-ok { color: #3fb950; opacity: 0.75; }
  .text.log-failed { color: var(--error); font-weight: 600; }
  .text.log-check { color: var(--accent); }
  .text.log-op { color: var(--text); font-weight: 600; }
  .text.log-summary {
    color: var(--text);
    font-weight: 700;
    border-top: 1px solid var(--border-muted);
    padding-top: 4px;
    margin-top: 4px;
    display: block;
  }

  .cursor {
    display: inline-block;
    color: var(--accent);
    animation: blink 0.8s step-end infinite;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }

  /* Responsive */
  @media (max-width: 900px) {
    .layout { grid-template-columns: 260px 1fr; }
    .field-row { grid-template-columns: 1fr; }
  }

  @media (max-width: 768px) {
    .layout {
      grid-template-columns: 1fr;
      grid-template-rows: auto 1fr;
    }
    aside {
      border-right: none;
      border-bottom: 1px solid var(--border);
      max-height: 45vh;
    }
  }
</style>
