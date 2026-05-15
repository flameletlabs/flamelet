<script>
  import { onMount } from 'svelte'
  import { getOperations } from '../lib/api.js'

  let ops = []
  let filter = ''
  let filtered = []

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
    <span class="count mono">{ops.length} tasks</span>
    <input type="search" placeholder="filter…" bind:value={filter} />
  </div>

  <div class="table-wrap">
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
    padding: 12px 24px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-2);
  }

  .title {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .count {
    font-size: 11px;
    color: var(--text-muted);
  }

  input {
    margin-left: auto;
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--mono);
    font-size: 12px;
    padding: 5px 10px;
    border-radius: 2px;
    width: 200px;
    outline: none;
  }

  input:focus {
    border-color: var(--accent);
  }

  .table-wrap {
    flex: 1;
    overflow-y: auto;
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
    padding: 10px 16px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
    background: var(--bg-2);
    position: sticky;
    top: 0;
    z-index: 1;
  }

  td {
    padding: 9px 16px;
    border-bottom: 1px solid var(--border-muted);
  }

  tr:hover td {
    background: var(--bg-2);
  }

  .col-num {
    width: 44px;
    color: var(--text-dim);
    font-size: 11px;
  }

  .task-name {
    font-size: 13px;
    font-weight: 700;
    color: var(--text);
  }

  .attr {
    font-size: 12px;
    color: var(--text-muted);
  }

  .os-col {
    text-align: center;
    width: 80px;
  }

  .check {
    font-family: var(--mono);
    font-size: 13px;
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
    font-family: var(--mono);
    font-size: 10px;
    padding: 1px 6px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 2px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
</style>
