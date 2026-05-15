<script>
  import { onMount } from 'svelte'
  import { getOperations } from '../lib/api.js'

  let ops = []
  let filter = ''
  let filtered = []
  let expandedOp = null
  let copiedText = null

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
    copiedText = text
    setTimeout(() => {
      copiedText = null
    }, 2000)
  }

  onMount(async () => {
    ops = await getOperations()
    updateFiltered()
  })

  function updateFiltered() {
    filtered = filter
      ? ops.filter(o =>
          o.task.includes(filter) || (o.config_attr || '').toLowerCase().includes(filter)
        )
      : ops
  }

  $: if (filter !== undefined) updateFiltered()

  function hasOS(op, os) {
    return !op.os_families || op.os_families.includes(os)
  }
</script>

<div class="page">
  <div class="toolbar">
    <span class="title">OPERATIONS</span>
    <span class="count">{ops.length} tasks</span>
    <input type="search" placeholder="filter…" bind:value={filter} />
  </div>

  <div class="content-wrap">
    <!-- Desktop: Table -->
    <div class="table-view">
      <table>
        <thead>
          <tr>
            <th class="col-num">#</th>
            <th>TASK</th>
            <th>CONFIG ATTR</th>
            <th>TYPE</th>
            <th class="os-col">LINUX</th>
            <th class="os-col">FREEBSD</th>
            <th class="os-col">OPENBSD</th>
          </tr>
        </thead>
        <tbody>
          {#each filtered as op, i}
            <tr>
              <td class="col-num mono">{(i + 1).toString().padStart(2, '0')}</td>
              <td class="mono task-name">{op.task}</td>
              <td class="mono attr">{op.config_attr || '—'}</td>
              <td><span class="badge type-badge">{op.op_type}</span></td>
              <td class="os-col">
                {#if hasOS(op, 'Linux')}<span class="check linux">✓</span>{:else}<span class="dash">—</span>{/if}
              </td>
              <td class="os-col">
                {#if hasOS(op, 'FreeBSD')}<span class="check freebsd">✓</span>{:else}<span class="dash">—</span>{/if}
              </td>
              <td class="os-col">
                {#if hasOS(op, 'OpenBSD')}<span class="check openbsd">✓</span>{:else}<span class="dash">—</span>{/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Mobile: Cards -->
    <div class="cards-view">
      {#each filtered as op, i (op.task)}
        <div class="op-card" class:expanded={expandedOp === op.task} style="animation-delay: {i * 50}ms;">
          <div class="card-header" role="button" tabindex="0" on:click={() => expandedOp = expandedOp === op.task ? null : op.task} on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && (expandedOp = expandedOp === op.task ? null : op.task)}>
            <span class="op-toggle">›</span>
            <span class="op-num">{(i + 1).toString().padStart(2, '0')}</span>
            <div class="op-title">{op.task}</div>
            <span class="status-dot healthy"></span>
            <span class="op-badge">{op.op_type}</span>
          </div>
          {#if op.config_attr}
            <div class="card-meta mono">{op.config_attr}</div>
          {/if}
          <div class="os-row">
            <span class="os-item" class:active={hasOS(op, 'Linux')}>Linux</span>
            <span class="os-item" class:active={hasOS(op, 'FreeBSD')}>FreeBSD</span>
            <span class="os-item" class:active={hasOS(op, 'OpenBSD')}>OpenBSD</span>
          </div>
          {#if expandedOp === op.task}
            <div class="op-details">
              {#if op.config_attr}
                <div class="detail-section">
                  <div class="detail-label">Configuration</div>
                  <div class="config-hint">
                    Config attr: <span class="mono">{op.config_attr}</span>
                    <button class="copy-btn" on:click={() => copyToClipboard(op.config_attr)} title="Copy to clipboard">
                      {copiedText === op.config_attr ? '✓' : '⎘'}
                    </button>
                  </div>
                </div>
              {/if}
              <div class="detail-section">
                <div class="detail-label">Supported Platforms</div>
                <div class="platform-list">
                  {#each ['Linux', 'FreeBSD', 'OpenBSD'] as platform}
                    <span class="platform-item" class:active={hasOS(op, platform)}>
                      {platform}
                      {#if hasOS(op, platform)}
                        <span class="checkmark">✓</span>
                      {/if}
                    </span>
                  {/each}
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </div>
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 18px 28px;
    border-bottom: 1px solid var(--border);
    background: linear-gradient(90deg, var(--bg-2) 0%, rgba(15, 22, 41, 0.5) 100%);
    flex-wrap: wrap;
  }

  .title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .count {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-muted);
  }

  input {
    margin-left: auto;
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--ui);
    font-size: 13px;
    font-weight: 400;
    padding: 10px 12px;
    border-radius: 6px;
    width: 200px;
    outline: none;
    min-height: 40px;
    transition: all 200ms;
  }

  input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.1);
  }

  .content-wrap {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
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
    gap: 16px;
    padding: 24px 28px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  thead tr {
    border-bottom: 1px solid var(--border);
  }

  th {
    text-align: left;
    padding: 12px 16px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    text-transform: uppercase;
    background: var(--bg-2);
    position: sticky;
    top: 0;
    z-index: 1;
  }

  td {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-muted);
    font-size: 13px;
  }

  tr:hover td {
    background: var(--bg-3);
  }

  .col-num {
    width: 50px;
    color: var(--text-dim);
    font-size: 12px;
  }

  .task-name {
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
  }

  .attr {
    font-size: 12px;
    color: var(--text-muted);
  }

  .os-col {
    text-align: center;
    width: 90px;
  }

  .check {
    font-size: 16px;
    font-weight: 700;
  }

  .check.linux {
    color: var(--linux);
  }

  .check.freebsd {
    color: var(--freebsd);
  }

  .check.openbsd {
    color: var(--openbsd);
  }

  .dash {
    color: var(--text-dim);
  }

  .type-badge {
    font-size: 11px;
    padding: 4px 8px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
  }

  /* Mobile: Card view */
  .op-card {
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px 24px;
    animation: slideIn 300ms ease-out forwards;
    opacity: 0;
    min-height: 44px;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    cursor: pointer;
    user-select: none;
  }

  .op-toggle {
    display: inline-block;
    font-size: 16px;
    color: var(--text-muted);
    transform: rotate(0deg);
    transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1);
    min-width: 20px;
    text-align: center;
  }

  .op-card.expanded .op-toggle {
    transform: rotate(90deg);
  }

  .op-num {
    font-family: var(--mono);
    font-size: clamp(11px, 2.5vw, 13px);
    font-weight: 700;
    color: var(--text-dim);
    min-width: 28px;
  }

  .status-dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    animation: pulse-dot 2s ease-in-out infinite;
  }

  .status-dot.healthy {
    background: var(--success);
  }

  @keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }

  .op-title {
    flex: 1;
    font-size: clamp(14px, 3.5vw, 16px);
    font-weight: 700;
    color: var(--text);
    font-family: var(--ui);
  }

  .op-badge {
    font-size: 10px;
    padding: 4px 8px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
    white-space: nowrap;
  }

  .card-meta {
    font-size: clamp(12px, 2.5vw, 13px);
    color: var(--text-muted);
    margin-bottom: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
    font-family: var(--ui);
  }

  .os-row {
    display: flex;
    gap: 8px;
  }

  .os-item {
    flex: 1;
    padding: 8px;
    text-align: center;
    font-size: clamp(11px, 2.2vw, 12px);
    font-weight: 600;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-dim);
    transition: all 200ms;
    min-height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .os-item.active {
    border-color: var(--accent);
    background: rgba(0, 212, 170, 0.1);
    color: var(--accent);
  }

  @media (max-width: 900px) {
    .toolbar {
      padding: 12px 14px;
      gap: 12px;
    }

    input {
      width: 160px;
      font-size: 12px;
      padding: 8px 10px;
    }
  }

  @media (max-width: 768px) {
    .table-view {
      display: none;
    }

    .cards-view {
      display: flex;
    }

    .toolbar {
      padding: 12px 12px;
      gap: 10px;
    }

    .title {
      font-size: 10px;
    }

    .count {
      font-size: 11px;
    }

    input {
      flex: 1 100%;
      margin-left: 0;
      order: 3;
      width: 100%;
      font-size: 12px;
      padding: 8px 10px;
      min-height: 40px;
    }
  }

  @media (max-width: 640px) {
    .toolbar {
      padding: 10px 10px;
      gap: 8px;
    }

    .cards-view {
      padding: 10px 10px;
      gap: 10px;
    }

    .op-card {
      padding: 12px;
    }

    .card-header {
      gap: 8px;
      margin-bottom: 8px;
    }

    .op-title {
      font-size: 13px;
    }

    .op-badge {
      font-size: 9px;
      padding: 3px 6px;
    }

    .card-meta {
      font-size: 11px;
      padding-bottom: 8px;
      margin-bottom: 8px;
    }

    .os-row {
      gap: 6px;
    }

    .os-item {
      padding: 6px;
      font-size: 10px;
    }
  }

  .op-details {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 10px;
    animation: expandIn 200ms ease-out;
  }

  @keyframes expandIn {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .detail-section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .detail-label {
    font-size: clamp(10px, 1.8vw, 11px);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-dim);
  }

  .config-hint {
    font-size: clamp(11px, 2vw, 12px);
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .copy-btn {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 11px;
    padding: 3px 6px;
    border-radius: 2px;
    cursor: pointer;
    transition: all 150ms;
    flex-shrink: 0;
    min-width: 24px;
    text-align: center;
  }

  .copy-btn:hover {
    border-color: var(--accent);
    background: var(--bg-3);
    color: var(--accent);
  }

  .copy-btn:active {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }

  .platform-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .platform-item {
    font-size: clamp(11px, 2vw, 12px);
    padding: 4px 8px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 3px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .platform-item.active {
    background: rgba(63, 185, 80, 0.15);
    border-color: var(--success);
    color: var(--success);
  }

  .checkmark {
    font-weight: 700;
  }

  @media (max-width: 480px) {
    .toolbar {
      padding: 8px 8px;
    }

    .cards-view {
      padding: 8px 8px;
    }

    input {
      font-size: 11px;
    }

    .op-card {
      padding: 10px;
    }

    .card-header {
      gap: 6px;
    }

    .op-num {
      font-size: 11px;
    }

    .op-title {
      font-size: 12px;
    }
  }
</style>
