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
    selectedHosts = new Set()
  }

  function toggleHost(name) {
    const next = new Set(selectedHosts)
    next.has(name) ? next.delete(name) : next.add(name)
    selectedHosts = next
  }

  function selectAll() {
    selectedHosts = new Set(hosts.map(h => h.name))
  }

  function selectNone() {
    selectedHosts = new Set()
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
        <select bind:value={selectedTenant} on:change={loadHosts}>
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
          <button class="link-btn" on:click={selectAll}>
            all
          </button>
          /
          <button class="link-btn" on:click={selectNone}> none </button>
        </div>
        {#each hosts as h}
          <label class="host-row">
            <input
              type="checkbox"
              checked={selectedHosts.has(h.name)}
              on:change={() => toggleHost(h.name)}
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

      <button class="run-btn" on:click={startRun} disabled={running || !selectedHosts.size}>
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
    padding: 18px 28px 14px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
    border-bottom: 1px solid var(--border-muted);
    background: linear-gradient(90deg, var(--bg-2) 0%, rgba(15, 22, 41, 0.5) 100%);
  }

  .form-body {
    padding: 28px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  label:not(.host-row):not(.dry-row) {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  label span {
    font-size: clamp(10px, 1.8vw, 11px);
    font-weight: 600;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  select {
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--ui);
    font-size: 13px;
    font-weight: 500;
    padding: 10px 12px;
    border-radius: 6px;
    cursor: pointer;
    outline: none;
    min-height: 44px;
    transition: all 200ms;
    -webkit-appearance: none;
    appearance: none;
  }

  select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.1);
  }

  .host-section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .section-label {
    font-size: clamp(9px, 1.6vw, 10px);
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
    gap: 10px;
    padding: 10px 10px;
    border-radius: 6px;
    cursor: pointer;
    min-height: 44px;
    transition: background 200ms;
  }

  .host-row:hover {
    background: var(--bg-3);
  }

  .host-row:active {
    background: rgba(0, 212, 170, 0.1);
  }

  .host-name {
    font-size: clamp(11px, 2.5vw, 12px);
    flex: 1;
    color: var(--text-muted);
    font-family: var(--ui);
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
    margin-top: 12px;
    padding: 14px 16px;
    background: var(--accent);
    border: none;
    color: var(--bg);
    font-family: var(--ui);
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.04em;
    cursor: pointer;
    border-radius: 8px;
    transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
    min-height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .run-btn:hover:not(:disabled) {
    background: #00c99f;
    box-shadow: 0 4px 12px rgba(0, 212, 170, 0.3);
    transform: translateY(-2px);
  }

  .run-btn:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 2px 6px rgba(0, 212, 170, 0.2);
  }

  .run-btn:disabled {
    opacity: 0.5;
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
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    background: linear-gradient(90deg, var(--bg-2) 0%, rgba(15, 22, 41, 0.5) 100%);
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

  @media (max-width: 900px) {
    .layout {
      grid-template-columns: 240px 1fr;
    }

    aside {
      max-height: none;
    }

    .form-body {
      gap: clamp(12px, 1.5vw, 16px);
      padding: clamp(12px, 1.5vw, 16px);
    }

    label span {
      font-size: 9px;
    }

    select {
      font-size: clamp(10px, 1.3vw, 11px);
    }

    .host-name {
      font-size: 10px;
    }
  }

  @media (max-width: 768px) {
    .layout {
      grid-template-columns: 1fr;
      grid-template-rows: auto 1fr;
    }

    aside {
      border-right: none;
      border-bottom: 1px solid var(--border);
      max-height: 35vh;
      overflow-y: auto;
    }

    .terminal-panel {
      min-height: 0;
    }

    .form-body {
      padding: clamp(12px, 1.5vw, 14px);
      gap: clamp(10px, 1.2vw, 14px);
    }

    .host-section {
      max-height: 120px;
      overflow-y: auto;
    }

    .terminal {
      padding: clamp(10px, 1.5vw, 14px);
      font-size: clamp(10px, 1.3vw, 11px);
    }
  }

  @media (max-width: 640px) {
    .form-body {
      padding: clamp(10px, 1.2vw, 12px);
      gap: clamp(8px, 1vw, 10px);
    }

    label span {
      font-size: 8px;
    }

    select {
      font-size: clamp(9px, 1.2vw, 10px);
      padding: clamp(4px, 0.6vw, 6px) clamp(6px, 1vw, 8px);
    }

    .section-label {
      font-size: 8px;
    }

    .host-name {
      font-size: 9px;
    }

    .terminal-header {
      padding: clamp(6px, 1vw, 8px) clamp(10px, 1.5vw, 12px);
      font-size: 8px;
    }

    .terminal {
      padding: clamp(8px, 1.2vw, 10px) clamp(8px, 1.5vw, 12px);
      font-size: clamp(9px, 1.2vw, 10px);
      line-height: 1.6;
    }

    .log-line {
      gap: clamp(8px, 1.2vw, 10px);
    }

    .ts {
      font-size: clamp(8px, 1vw, 9px);
      min-width: 60px;
    }
  }

  @media (max-width: 480px) {
    .host-section {
      max-height: 100px;
    }

    .form-body {
      padding: 8px 10px;
      gap: 6px;
    }

    select {
      font-size: 9px;
      padding: 3px 5px;
    }

    .terminal {
      font-size: 9px;
      padding: 8px;
    }
  }
</style>
