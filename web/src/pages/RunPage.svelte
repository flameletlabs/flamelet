<script>
  import { onMount, tick } from 'svelte'
  import { getTenants, getTenantHosts, postRun } from '../lib/api.js'

  let tenants = []
  let hosts = []
  let tasks = [
    'users', 'sudo', 'packages', 'sysctl', 'services', 'wireguard', 'monit',
    'unbound', 'pf', 'docker', 'node_exporter', 'k3s', 'bhyve', 'jails',
    'storage', 'nginx', 'postgresql', 'prometheus', 'registry', 'autossh',
    'opensmtpd', 'all'
  ]

  let selectedTenant = ''
  let selectedTask = 'sysctl'
  let selectedHosts = new Set()
  let dryRun = true

  let runId = null
  let running = false
  let status = null
  let logLines = []
  let logEl = null

  onMount(async () => {
    tenants = await getTenants()
    if (tenants.length) {
      selectedTenant = tenants[0].name
      await loadHosts()
    }
  })

  async function loadHosts() {
    hosts = await getTenantHosts(selectedTenant)
    selectedHosts = new Set(hosts.map(h => h.name))
  }

  function toggleHost(name) {
    const next = new Set(selectedHosts)
    next.has(name) ? next.delete(name) : next.add(name)
    selectedHosts = next
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
    })
    runId = res.run_id
    streamLogs(runId)
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
    <div class="form-header">NEW RUN</div>
    <div class="form-body">
      <label>
        <span>Tenant</span>
        <select bind:value={selectedTenant} onchange={loadHosts}>
          {#each tenants as t}
            <option value={t.name}>{t.name}</option>
          {/each}
        </select>
      </label>

      <label>
        <span>Task</span>
        <select bind:value={selectedTask}>
          {#each tasks as t}
            <option value={t}>{t}</option>
          {/each}
        </select>
      </label>

      <div class="host-section">
        <div class="section-label">
          HOSTS
          <button class="link-btn" onclick={() => (selectedHosts = new Set(hosts.map(h => h.name)))}>
            all
          </button>
          /
          <button class="link-btn" onclick={() => (selectedHosts = new Set())}> none </button>
        </div>
        {#each hosts as h}
          <label class="host-row">
            <input
              type="checkbox"
              checked={selectedHosts.has(h.name)}
              onchange={() => toggleHost(h.name)}
            />
            <span class="mono host-name">{h.name}</span>
            <span class="badge badge-{h.os.toLowerCase()}">{h.os}</span>
          </label>
        {/each}
      </div>

      <label class="dry-row">
        <input type="checkbox" bind:checked={dryRun} />
        <span>Dry run (no changes)</span>
      </label>

      <button class="run-btn" onclick={startRun} disabled={running || !selectedHosts.size}>
        {running ? '● RUNNING...' : '▶ RUN'}
      </button>
    </div>
  </aside>

  <section class="terminal-panel">
    <div class="terminal-header">
      <span>OUTPUT</span>
      {#if running}
        <span class="live-badge">● LIVE</span>
      {:else if status}
        <span class="badge badge-{status}">{status.toUpperCase()}</span>
      {/if}
    </div>
    <div class="terminal" bind:this={logEl}>
      {#if logLines.length === 0 && !running}
        <span class="prompt">$ flamelet --task {selectedTask} {dryRun ? '--dry' : ''}</span>
      {/if}
      {#each logLines as line}
        <div class="log-line">
          <span class="ts">[{line.ts}]</span>
          <span
            class="text"
            class:success={line.text.includes('ok, 0 errors')}
            class:error={line.text.includes('Error')}>{line.text}</span
          >
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
    grid-template-columns: 280px 1fr;
    height: 100%;
  }

  aside {
    border-right: 1px solid var(--border);
    background: var(--bg-2);
    overflow-y: auto;
  }

  .form-header {
    padding: 12px 20px 8px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
    border-bottom: 1px solid var(--border-muted);
  }

  .form-body {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  label:not(.host-row):not(.dry-row) {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  label span {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  select {
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--mono);
    font-size: 12px;
    padding: 6px 10px;
    border-radius: 2px;
    cursor: pointer;
    outline: none;
  }

  select:focus {
    border-color: var(--accent);
  }

  .host-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    text-transform: uppercase;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .link-btn {
    background: none;
    border: none;
    color: var(--accent);
    cursor: pointer;
    font-size: 10px;
    padding: 0;
  }

  .host-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 8px;
    border-radius: 2px;
    cursor: pointer;
  }

  .host-row:hover {
    background: var(--bg-3);
  }

  .host-name {
    font-size: 11px;
    flex: 1;
    color: var(--text-muted);
  }

  .dry-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text-muted);
    cursor: pointer;
  }

  input[type='checkbox'] {
    accent-color: var(--accent);
  }

  .run-btn {
    margin-top: 4px;
    padding: 10px;
    background: var(--accent-bg);
    border: 1px solid var(--accent);
    color: var(--accent);
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.1em;
    cursor: pointer;
    border-radius: 2px;
    transition: background 0.15s;
  }

  .run-btn:hover:not(:disabled) {
    background: rgba(0, 212, 170, 0.18);
  }

  .run-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .terminal-panel {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .terminal-header {
    display: flex;
    align-items: center;
    gap: 12px;
    justify-content: space-between;
    padding: 10px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-2);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .live-badge {
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    color: var(--running);
    letter-spacing: 0.08em;
    animation: pulse 1.2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.4;
    }
  }

  .terminal {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    font-family: var(--mono);
    font-size: 12px;
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

  .prompt {
    color: var(--text-dim);
  }

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

  .text.success {
    color: var(--success);
    font-weight: 700;
  }

  .text.error {
    color: var(--error);
  }

  .cursor {
    display: inline-block;
    color: var(--accent);
    animation: blink 0.8s step-end infinite;
  }

  @keyframes blink {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0;
    }
  }
</style>
