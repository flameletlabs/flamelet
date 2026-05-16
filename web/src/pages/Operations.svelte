<script>
  import { onMount } from 'svelte'
  import { getOperations } from '../lib/api.js'

  let { tenant = null } = $props()

  let opsRaw = $state([])
  let filter = $state('')
  let copiedText = $state(null)
  let expandedOp = $state(null)

  onMount(async () => {
    opsRaw = await getOperations()
  })

  // Group multi-entry tasks (autossh has TUNNELS + GATEWAY as two entries)
  let ops = $derived.by(() => {
    const map = new Map()
    for (const op of opsRaw) {
      if (map.has(op.task)) {
        const existing = map.get(op.task)
        if (op.config_attr && !existing.config_attrs.includes(op.config_attr)) {
          existing.config_attrs.push(op.config_attr)
        }
      } else {
        map.set(op.task, {
          task: op.task,
          config_attrs: op.config_attr ? [op.config_attr] : [],
          op_type: op.op_type,
          os_families: op.os_families,
        })
      }
    }
    return [...map.values()]
  })

  let filtered = $derived.by(() => {
    const q = filter.toLowerCase()
    if (!q) return ops
    return ops.filter(o =>
      o.task.includes(q) ||
      o.config_attrs.some(a => a.toLowerCase().includes(q)) ||
      (o.op_type || '').includes(q)
    )
  })

  function hasOS(op, os) {
    return !op.os_families || op.os_families.includes(os)
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
    copiedText = text
    setTimeout(() => copiedText = null, 2000)
  }

  function toggleOp(task) {
    expandedOp = expandedOp === task ? null : task
  }

  const TYPE_COLORS = {
    standard:  { bg: 'rgba(68, 147, 248, 0.12)',   border: '#4493f8',                    text: '#4493f8', stripe: '#4493f8' },
    autossh:   { bg: 'rgba(240, 136, 62, 0.12)',   border: '#f0883e',                    text: '#f0883e', stripe: '#f0883e' },
    packages:  { bg: 'rgba(63, 185, 80, 0.12)',    border: '#3fb950',                    text: '#3fb950', stripe: '#3fb950' },
    users:     { bg: 'rgba(0, 212, 170, 0.12)',    border: '#00d4aa',                    text: '#00d4aa', stripe: '#00d4aa' },
    sudo:      { bg: 'rgba(0, 212, 170, 0.12)',    border: '#00d4aa',                    text: '#00d4aa', stripe: '#00d4aa' },
  }

  function typeStyle(op_type) {
    const c = TYPE_COLORS[op_type] || TYPE_COLORS.standard
    return `--op-bg:${c.bg}; --op-border:${c.border}; --op-text:${c.text}; --op-stripe:${c.stripe}`
  }

  const OS_LIST = ['Linux', 'FreeBSD', 'OpenBSD']
</script>

<div class="page">
  <!-- Header with search -->
  <div class="toolbar">
    <div class="toolbar-left">
      <span class="title">OPERATIONS</span>
      <span class="count">{ops.length} available</span>
    </div>
    <div class="search-wrap">
      <span class="search-icon">⌕</span>
      <input type="search" placeholder="filter…" bind:value={filter} />
    </div>
  </div>

  <!-- Unified list (works both desktop and mobile) -->
  <div class="ops-container">
    <div class="ops-list">
      {#each filtered as op, i (op.task)}
        <button
          class="op-row"
          class:expanded={expandedOp === op.task}
          style={typeStyle(op.op_type)}
          onclick={() => toggleOp(op.task)}>

          <!-- Left accent stripe (operation type color) -->
          <span class="op-stripe"></span>

          <!-- Row content -->
          <div class="op-content">
            <!-- Top section: number, name, type -->
            <div class="op-header">
              <span class="op-num">{(i + 1).toString().padStart(2, '0')}</span>
              <span class="op-name">{op.task}</span>
              <span class="op-type-badge">{op.op_type}</span>
            </div>

            <!-- Bottom section: OS support + expand indicator -->
            <div class="op-footer">
              <div class="op-os-support">
                {#each OS_LIST as os}
                  <span class="os-indicator os-{os.toLowerCase()}" class:supported={hasOS(op, os)} title={os}>
                    {hasOS(op, os) ? '●' : '○'}
                  </span>
                {/each}
              </div>
              <span class="op-expand-icon" class:open={expandedOp === op.task}>›</span>
            </div>
          </div>
        </button>

        <!-- Expanded detail panel -->
        {#if expandedOp === op.task}
          <div class="op-detail-panel" style={typeStyle(op.op_type)}>
            <div class="detail-header">
              <span class="detail-title">{op.task}</span>
              <button class="detail-close" onclick={() => toggleOp(op.task)}>✕</button>
            </div>

            <div class="detail-content">
              <!-- Operation type -->
              <div class="detail-section">
                <div class="detail-label">Type</div>
                <span class="op-type-badge large">{op.op_type}</span>
              </div>

              <!-- Config attributes -->
              {#if op.config_attrs.length > 0}
                <div class="detail-section">
                  <div class="detail-label">Config Attributes</div>
                  <div class="attrs-grid">
                    {#each op.config_attrs as attr}
                      <button class="attr-chip" onclick={() => copyToClipboard(attr)} title="Click to copy">
                        <span class="mono">{attr}</span>
                        <span class="copy-icon">{copiedText === attr ? '✓' : '⎘'}</span>
                      </button>
                    {/each}
                  </div>
                </div>
              {:else}
                <div class="detail-section">
                  <div class="detail-label">Config</div>
                  <div class="detail-note">loaded from vars/__init__.py</div>
                </div>
              {/if}

              <!-- OS support detail -->
              <div class="detail-section">
                <div class="detail-label">Supported OS</div>
                <div class="os-support-list">
                  {#each OS_LIST as os}
                    <div class="os-support-item">
                      <span class="os-indicator-large os-{os.toLowerCase()}" class:supported={hasOS(op, os)}>
                        {hasOS(op, os) ? '●' : '○'}
                      </span>
                      <span>{os}</span>
                    </div>
                  {/each}
                </div>
              </div>
            </div>
          </div>
        {/if}
      {/each}

      {#if filtered.length === 0}
        <div class="empty">
          {ops.length === 0 ? 'Loading…' : `No operations match "${filter}"`}
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  :root {
    --op-bg: transparent;
    --op-border: transparent;
    --op-text: inherit;
    --op-stripe: var(--accent);
  }

  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  /* ── TOOLBAR ────────────────────────────────────────────────── */
  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 14px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-2);
    flex-shrink: 0;
  }

  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .title {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .count {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text-muted);
  }

  .search-wrap {
    position: relative;
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

  input {
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--mono);
    font-size: 12px;
    padding: 10px 12px 10px 30px;
    border-radius: 4px;
    width: 200px;
    outline: none;
    transition: border-color 150ms, box-shadow 150ms;
    min-height: 44px;
  }

  input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.1);
  }

  input::placeholder {
    color: var(--text-dim);
  }

  /* ── OPERATIONS LIST CONTAINER ──────────────────────────────── */
  .ops-container {
    flex: 1;
    display: flex;
    overflow: hidden;
    position: relative;
  }

  .ops-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    background: var(--bg);
  }

  /* ── OPERATION ROW (Command Center Design) ──────────────────── */
  .op-row {
    position: relative;
    display: flex;
    align-items: stretch;
    width: 100%;
    background: none;
    border: none;
    border-bottom: 1px solid var(--border-muted);
    padding: 0;
    cursor: pointer;
    text-align: left;
    transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  .op-row:hover {
    background: var(--op-bg);
  }

  .op-row.expanded {
    background: var(--op-bg);
    border-bottom-color: var(--op-border);
  }

  .op-row:last-of-type {
    border-bottom: none;
  }

  /* Left accent stripe (operation type color) */
  .op-stripe {
    width: 4px;
    flex-shrink: 0;
    background: var(--op-stripe);
    opacity: 0.9;
  }

  /* Row content wrapper */
  .op-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 14px 18px;
    min-height: 0;
    gap: 10px;
  }

  /* Top: number, name, type */
  .op-header {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 0;
  }

  .op-num {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text-dim);
    flex-shrink: 0;
    min-width: 28px;
  }

  .op-name {
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 700;
    color: var(--text);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .op-type-badge {
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 3px 8px;
    background: var(--op-bg);
    border: 1px solid var(--op-border);
    color: var(--op-text);
    border-radius: 3px;
    flex-shrink: 0;
    white-space: nowrap;
  }

  /* Bottom: OS support + expand icon */
  .op-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .op-os-support {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .os-indicator {
    font-size: 11px;
    font-weight: 700;
    color: var(--text-muted);
    transition: color 150ms;
  }

  .os-indicator.supported.os-linux { color: var(--linux); }
  .os-indicator.supported.os-freebsd { color: var(--freebsd); }
  .os-indicator.supported.os-openbsd { color: var(--openbsd); }

  .op-expand-icon {
    font-size: 16px;
    color: var(--text-muted);
    transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
    transform: rotate(0deg);
    flex-shrink: 0;
  }

  .op-expand-icon.open {
    transform: rotate(90deg);
    color: var(--op-text);
  }

  /* ── DETAIL PANEL (Bottom Sheet on Mobile, Side Panel on Desktop) ────── */
  .op-detail-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    top: auto;
    max-height: 70vh;
    background: var(--bg-2);
    border-top: 1px solid var(--border);
    border-left: 4px solid var(--op-stripe);
    border-right: none;
    border-bottom: none;
    z-index: 50;
    display: flex;
    flex-direction: column;
    animation: bottomSheetIn 250ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  @keyframes bottomSheetIn {
    from {
      transform: translateY(100%);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  .detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .detail-title {
    font-family: var(--mono);
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
  }

  .detail-close {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 18px;
    cursor: pointer;
    padding: 4px 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 150ms;
    min-height: 44px;
    min-width: 44px;
  }

  .detail-close:hover {
    color: var(--text);
  }

  .detail-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .detail-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .detail-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
  }

  .detail-note {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text-muted);
    font-style: italic;
  }

  /* Config attributes in detail panel */
  .attrs-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .attr-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: 8px 10px;
    font-size: 11px;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 100ms;
    text-align: left;
    white-space: nowrap;
    min-height: 32px;
    font-family: var(--mono);
  }

  .attr-chip:hover {
    border-color: var(--op-border);
    color: var(--text);
    background: var(--bg-3);
  }

  .copy-icon {
    font-size: 10px;
    flex-shrink: 0;
    margin-left: auto;
  }

  /* OS Support list in detail panel */
  .os-support-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .os-support-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text);
  }

  .os-indicator-large {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-muted);
  }

  .os-indicator-large.supported.os-linux { color: var(--linux); }
  .os-indicator-large.supported.os-freebsd { color: var(--freebsd); }
  .os-indicator-large.supported.os-openbsd { color: var(--openbsd); }

  .op-type-badge.large {
    display: inline-block;
  }

  /* ── EMPTY STATE ────────────────────────────────────────────── */
  .empty {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    font-family: var(--mono);
    font-size: 12px;
    padding: 40px;
    text-align: center;
  }

  /* ──────── RESPONSIVE: TABLET ────────────────────────────────── */
  @media (max-width: 900px) {
    .toolbar {
      flex-wrap: wrap;
      padding: 10px 16px;
      gap: 8px;
    }

    .search-wrap {
      width: 100%;
      order: 3;
    }

    input {
      width: 100%;
      box-sizing: border-box;
    }

    .op-content {
      padding: 12px 14px;
      gap: 8px;
    }

    .op-name {
      font-size: 12px;
    }

    .op-type-badge {
      font-size: 9px;
    }
  }

  /* ──────── RESPONSIVE: MOBILE ────────────────────────────────── */
  @media (max-width: 640px) {
    .toolbar {
      padding: 8px 12px;
      gap: 6px;
    }

    .title,
    .count {
      font-size: 10px;
    }

    input {
      width: 100%;
      padding: 8px 10px 8px 28px;
      font-size: 11px;
    }

    .op-row {
      min-height: 48px;
    }

    .op-content {
      padding: 10px 12px;
      gap: 6px;
    }

    .op-header {
      gap: 8px;
    }

    .op-num {
      font-size: 10px;
      min-width: 24px;
    }

    .op-name {
      font-size: 12px;
    }

    .op-type-badge {
      font-size: 8px;
      padding: 2px 6px;
    }

    .op-footer {
      gap: 8px;
    }

    .os-indicator {
      font-size: 10px;
    }

    .op-expand-icon {
      font-size: 14px;
    }

    /* Detail panel full height on mobile */
    .op-detail-panel {
      max-height: 80vh;
    }

    .detail-header {
      padding: 12px 16px;
    }

    .detail-content {
      padding: 12px 16px;
      gap: 16px;
    }

    .detail-title {
      font-size: 13px;
    }

    .attrs-grid {
      gap: 4px;
    }

    .attr-chip {
      padding: 6px 8px;
      font-size: 10px;
      min-height: 28px;
    }

    .os-support-item {
      font-size: 11px;
    }
  }

  /* ──────── VERY SMALL PHONES ────────────────────────────────── */
  @media (max-width: 360px) {
    .op-content {
      padding: 8px 10px;
    }

    .op-header {
      gap: 6px;
    }

    .op-name {
      font-size: 11px;
    }
  }
</style>
