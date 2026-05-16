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

  const TYPE_COLORS = {
    standard:  { bg: 'rgba(68, 147, 248, 0.1)',  border: 'rgba(68, 147, 248, 0.3)',  text: '#4493f8' },
    autossh:   { bg: 'rgba(240, 136, 62, 0.1)',  border: 'rgba(240, 136, 62, 0.3)',  text: '#f0883e' },
    packages:  { bg: 'rgba(63, 185, 80, 0.1)',   border: 'rgba(63, 185, 80, 0.3)',   text: '#3fb950' },
    users:     { bg: 'rgba(0, 212, 170, 0.1)',   border: 'rgba(0, 212, 170, 0.3)',   text: '#00d4aa' },
    sudo:      { bg: 'rgba(0, 212, 170, 0.1)',   border: 'rgba(0, 212, 170, 0.3)',   text: '#00d4aa' },
  }

  function typeStyle(op_type) {
    const c = TYPE_COLORS[op_type] || TYPE_COLORS.standard
    return `background:${c.bg}; border-color:${c.border}; color:${c.text}`
  }

  const OS_LIST = ['Linux', 'FreeBSD', 'OpenBSD']
</script>

<div class="page">
  <div class="toolbar">
    <div class="toolbar-left">
      <span class="title">OPERATIONS</span>
      <span class="count">{ops.length} tasks</span>
    </div>
    <div class="search-wrap">
      <span class="search-icon">⌕</span>
      <input type="search" placeholder="filter tasks…" bind:value={filter} />
    </div>
  </div>

  <!-- Desktop table -->
  <div class="table-scroll">
    <table>
      <thead>
        <tr>
          <th class="col-num">#</th>
          <th class="col-task">TASK</th>
          <th class="col-attr">CONFIG ATTR</th>
          <th class="col-type">TYPE</th>
          {#each OS_LIST as os}
            <th class="col-os">{os.toUpperCase()}</th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each filtered as op, i}
          <tr class:expanded={expandedOp === op.task}
              onclick={() => expandedOp = expandedOp === op.task ? null : op.task}
              role="button" tabindex="0"
              onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (expandedOp = expandedOp === op.task ? null : op.task)}>
            <td class="col-num dim">{(i + 1).toString().padStart(2, '0')}</td>
            <td class="col-task">
              <span class="task-name">{op.task}</span>
            </td>
            <td class="col-attr">
              {#if op.config_attrs.length === 0}
                <span class="dash">—</span>
              {:else}
                <div class="attr-list">
                  {#each op.config_attrs as attr}
                    <button class="attr-chip" onclick={(e) => { e.stopPropagation(); copyToClipboard(attr) }} title="Copy">
                      <span class="mono">{attr}</span>
                      <span class="copy-icon">{copiedText === attr ? '✓' : '⎘'}</span>
                    </button>
                  {/each}
                </div>
              {/if}
            </td>
            <td class="col-type">
              <span class="type-pill" style={typeStyle(op.op_type)}>{op.op_type}</span>
            </td>
            {#each OS_LIST as os}
              <td class="col-os">
                {#if hasOS(op, os)}
                  <span class="os-check os-{os.toLowerCase()}">✓</span>
                {:else}
                  <span class="dash">—</span>
                {/if}
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
    {#if filtered.length === 0 && ops.length > 0}
      <div class="empty">no tasks match "{filter}"</div>
    {:else if ops.length === 0}
      <div class="empty loading-msg">loading…</div>
    {/if}
  </div>

  <!-- Mobile cards -->
  <div class="cards-scroll">
    {#each filtered as op, i (op.task)}
      <div class="op-card" style="animation-delay:{i * 40}ms">
        <div class="card-head"
             role="button" tabindex="0"
             onclick={() => expandedOp = expandedOp === op.task ? null : op.task}
             onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (expandedOp = expandedOp === op.task ? null : op.task)}>
          <span class="card-num dim">{(i + 1).toString().padStart(2, '0')}</span>
          <span class="card-task">{op.task}</span>
          <span class="type-pill" style={typeStyle(op.op_type)}>{op.op_type}</span>
          <span class="chevron" class:open={expandedOp === op.task}>›</span>
        </div>

        <div class="card-os-row">
          {#each OS_LIST as os}
            <span class="os-pill" class:active={hasOS(op, os)} class:os-linux={os === 'Linux' && hasOS(op, os)} class:os-freebsd={os === 'FreeBSD' && hasOS(op, os)} class:os-openbsd={os === 'OpenBSD' && hasOS(op, os)}>
              {os}
            </span>
          {/each}
        </div>

        {#if expandedOp === op.task}
          <div class="card-detail">
            {#if op.config_attrs.length > 0}
              <div class="detail-label">CONFIG ATTR{op.config_attrs.length > 1 ? 'S' : ''}</div>
              <div class="attr-list">
                {#each op.config_attrs as attr}
                  <button class="attr-chip" onclick={() => copyToClipboard(attr)} title="Copy">
                    <span class="mono">{attr}</span>
                    <span class="copy-icon">{copiedText === attr ? '✓' : '⎘'}</span>
                  </button>
                {/each}
              </div>
            {:else}
              <div class="detail-label">No config attribute (loaded from vars/__init__.py)</div>
            {/if}
          </div>
        {/if}
      </div>
    {/each}
    {#if filtered.length === 0 && ops.length > 0}
      <div class="empty">no tasks match "{filter}"</div>
    {/if}
  </div>
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  /* ── Toolbar ─────────────────────────────────────────── */
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
    padding: 7px 12px 7px 30px;
    border-radius: 4px;
    width: 200px;
    outline: none;
    transition: border-color 150ms;
  }

  input:focus {
    border-color: var(--accent);
  }

  input::placeholder {
    color: var(--text-dim);
  }

  /* ── Table (desktop) ─────────────────────────────────── */
  .table-scroll {
    flex: 1;
    overflow-y: auto;
    overflow-x: auto;
  }

  .cards-scroll {
    display: none;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: var(--bg-2);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }

  tbody tr {
    cursor: pointer;
    border-bottom: 1px solid var(--border-muted);
    transition: background 80ms;
  }

  tbody tr:hover {
    background: var(--bg-2);
  }

  tbody tr.expanded {
    background: rgba(0, 212, 170, 0.04);
  }

  tbody tr:last-child {
    border-bottom: none;
  }

  td {
    padding: 11px 14px;
    vertical-align: middle;
  }

  .col-num {
    width: 44px;
    font-family: var(--mono);
    font-size: 11px;
    text-align: right;
    padding-right: 8px;
  }

  .col-task {
    min-width: 140px;
  }

  .col-attr {
    min-width: 180px;
  }

  .col-type {
    width: 110px;
  }

  .col-os {
    width: 80px;
    text-align: center;
  }

  .dim { color: var(--text-dim); }

  .task-name {
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 700;
    color: var(--text);
  }

  /* Config attr chips */
  .attr-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .attr-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-3);
    border: 1px solid var(--border-muted);
    border-radius: 3px;
    padding: 2px 7px;
    font-size: 11px;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 100ms;
    text-align: left;
    white-space: nowrap;
  }

  .attr-chip:hover {
    border-color: var(--accent);
    color: var(--text);
  }

  .copy-icon {
    font-size: 10px;
    color: var(--text-dim);
    flex-shrink: 0;
  }

  .attr-chip:hover .copy-icon {
    color: var(--accent);
  }

  /* Type badge */
  .type-pill {
    display: inline-block;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 2px 7px;
    border-radius: 3px;
    border: 1px solid;
    white-space: nowrap;
  }

  /* OS checks */
  .os-check {
    font-size: 13px;
    font-weight: 700;
  }

  .os-check.os-linux   { color: var(--linux); }
  .os-check.os-freebsd { color: var(--freebsd); }
  .os-check.os-openbsd { color: var(--openbsd); }

  .dash {
    color: var(--text-dim);
    font-size: 12px;
  }

  /* ── Empty / Loading ─────────────────────────────────── */
  .empty {
    padding: 40px;
    text-align: center;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-dim);
  }

  .loading-msg { color: var(--text-dim); }

  /* ── Mobile cards ────────────────────────────────────── */
  @media (max-width: 768px) {
    .table-scroll  { display: none; }
    .cards-scroll  {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 12px;
      flex: 1;
      overflow-y: auto;
    }

    .toolbar {
      flex-wrap: wrap;
      padding: 10px 12px;
      gap: 8px;
    }

    .search-wrap { width: 100%; order: 3; }
    input { width: 100%; box-sizing: border-box; }

    .op-card {
      background: var(--bg-2);
      border: 1px solid var(--border);
      border-radius: 6px;
      overflow: hidden;
      animation: card-in 280ms ease-out both;
    }

    @keyframes card-in {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .card-head {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 14px;
      cursor: pointer;
      user-select: none;
    }

    .card-num {
      font-family: var(--mono);
      font-size: 11px;
      min-width: 22px;
    }

    .card-task {
      font-family: var(--mono);
      font-size: 13px;
      font-weight: 700;
      color: var(--text);
      flex: 1;
    }

    .chevron {
      font-size: 14px;
      color: var(--text-dim);
      transition: transform 150ms;
      transform: rotate(0deg);
      line-height: 1;
    }

    .chevron.open {
      transform: rotate(90deg);
    }

    .card-os-row {
      display: flex;
      gap: 6px;
      padding: 0 14px 12px;
    }

    .os-pill {
      flex: 1;
      text-align: center;
      font-size: 10px;
      font-weight: 600;
      padding: 4px 6px;
      border-radius: 3px;
      background: var(--bg-3);
      border: 1px solid var(--border-muted);
      color: var(--text-dim);
    }

    .os-pill.os-linux   { background: rgba(68,147,248,0.1); border-color: rgba(68,147,248,0.3); color: var(--linux); }
    .os-pill.os-freebsd { background: rgba(205,123,106,0.1); border-color: rgba(205,123,106,0.3); color: var(--freebsd); }
    .os-pill.os-openbsd { background: rgba(227,179,65,0.1); border-color: rgba(227,179,65,0.3); color: var(--openbsd); }

    .card-detail {
      padding: 10px 14px 12px;
      border-top: 1px solid var(--border-muted);
      background: var(--bg-3);
      display: flex;
      flex-direction: column;
      gap: 6px;
      animation: slide-down 150ms ease-out;
    }

    @keyframes slide-down {
      from { opacity: 0; transform: translateY(-4px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .detail-label {
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--text-dim);
    }

    .attr-chip { font-size: 11px; }
  }

  @media (max-width: 480px) {
    .cards-scroll { padding: 8px; gap: 6px; }
    .card-head { padding: 10px 12px; }
    .card-os-row { padding: 0 12px 10px; }
    .card-task { font-size: 12px; }
  }
</style>
