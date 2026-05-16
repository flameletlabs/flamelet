<script>
  import { getTopology } from '../lib/api.js'

  let { tenant = null } = $props()

  let topology = $state(null)
  let selectedNode = $state(null)
  let hoveredEdge = $state(null)
  let loading = $state(false)
  let error = $state(null)

  const OS_COLORS = {
    openbsd: '#e3b341',
    freebsd: '#cd7b6a',
    linux: '#4493f8',
  }

  $effect(() => {
    if (!tenant) {
      topology = null
      selectedNode = null
      return
    }
    loadTopology()
  })

  async function loadTopology() {
    loading = true
    error = null
    try {
      topology = await getTopology(tenant)
      selectedNode = null
    } catch (e) {
      error = e.message
    }
    loading = false
  }

  function formatIP(addr) {
    return addr ? addr.split('/')[0] : '?'
  }

  function getSelectedNodePeers() {
    if (!selectedNode || !topology) return []
    const edges = topology.edges.filter(e => e.from === selectedNode || e.to === selectedNode)
    const peers = new Set()
    edges.forEach(e => {
      if (e.from === selectedNode) peers.add(e.to)
      else peers.add(e.from)
    })
    return Array.from(peers).sort()
  }

  // Hub-spoke radial layout: find node with most connections, place it center
  function computeLayout(nodes, edges) {
    if (!nodes?.length) return {}

    const SVG_W = 600, SVG_H = 480
    const CX = SVG_W / 2, CY = SVG_H / 2
    const NODE_W = 130, NODE_H = 44

    // Find hub: node with most wireguard edges
    const degree = {}
    edges.filter(e => e.type === 'wireguard').forEach(e => {
      degree[e.from] = (degree[e.from] || 0) + 1
      degree[e.to] = (degree[e.to] || 0) + 1
    })
    const sorted = [...nodes].sort((a, b) => (degree[b.id] || 0) - (degree[a.id] || 0))
    const hub = sorted[0]
    const spokes = sorted.slice(1)

    const pos = {}
    pos[hub.id] = { x: CX - NODE_W / 2, y: CY - NODE_H / 2 }

    const radius = Math.min(CX, CY) * 0.72
    spokes.forEach((n, i) => {
      const angle = (i / spokes.length) * Math.PI * 2 - Math.PI / 2
      pos[n.id] = {
        x: CX + Math.cos(angle) * radius - NODE_W / 2,
        y: CY + Math.sin(angle) * radius - NODE_H / 2,
      }
    })

    return pos
  }

  let layout = $derived.by(() => {
    if (!topology) return {}
    return computeLayout(topology.nodes, topology.edges)
  })

  function nodeCenter(id) {
    const p = layout[id]
    if (!p) return { x: 0, y: 0 }
    return { x: p.x + 65, y: p.y + 22 }
  }

  // Offset parallel lines so bidirectional edges sit side-by-side
  function offsetLine(x1, y1, x2, y2, isReverse, offset = 6) {
    const dx = x2 - x1
    const dy = y2 - y1
    const length = Math.sqrt(dx * dx + dy * dy)

    if (length === 0) return { x1, y1, x2, y2 }

    // Perpendicular vector (rotated 90 degrees)
    const px = (-dy / length) * offset
    const py = (dx / length) * offset

    // Apply offset: one direction positive, other negative
    const sign = isReverse ? -1 : 1
    return {
      x1: x1 + px * sign,
      y1: y1 + py * sign,
      x2: x2 + px * sign,
      y2: y2 + py * sign,
    }
  }

  // Check if there's a reverse edge
  function hasReverseEdge(edge) {
    return topology?.edges.some(
      e => e.type === edge.type && e.from === edge.to && e.to === edge.from
    )
  }
</script>

<div class="container">
  <div class="header">
    <span class="title">TOPOLOGY</span>
    <div class="controls">
      <button onclick={loadTopology} disabled={loading} class:loading>
        {loading ? '⟳' : '↺'} Refresh
      </button>
    </div>
  </div>

  <div class="main">
    <div class="sidebar">
      <div class="section">
        <h3>Locations</h3>
        {#if topology}
          {#each Object.entries(topology.locations || {}).sort() as [location, hosts]}
            <div class="location-item">
              <span class="dot" style="background: var(--accent);"></span>
              <span class="loc-name">{location}</span>
              <span class="count">{hosts.length}</span>
            </div>
          {/each}
        {/if}
      </div>

      <div class="section">
        <h3>Legend</h3>
        <div class="legend-item">
          <svg width="12" height="12"><line x1="0" y1="6" x2="12" y2="6" stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="6,3" /></svg>
          <span>WireGuard</span>
        </div>
        <div class="legend-item">
          <svg width="12" height="12"><line x1="0" y1="6" x2="12" y2="6" stroke="var(--running)" stroke-width="1" stroke-dasharray="4,4" /></svg>
          <span>AutoSSH</span>
        </div>
      </div>

      {#if selectedNode}
        <div class="section selected-info">
          <h3>{selectedNode}</h3>
          <p class="info-text">
            Peers: <span class="peer-count">{getSelectedNodePeers().length}</span>
          </p>
        </div>
      {/if}
    </div>

    <div class="diagram-container">
      {#if loading}
        <div class="loading">Loading topology...</div>
      {:else if error}
        <div class="error">{error}</div>
      {:else if topology}
        <svg viewBox="0 0 600 480" class="diagram" preserveAspectRatio="xMidYMid meet">
          <defs>
            <marker id="arrowhead-autossh" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <polygon points="0 0, 10 3, 0 6" fill="var(--running)" />
            </marker>
            <style>
              @keyframes dash-flow {{
                to {{ stroke-dashoffset: -18; }}
              }}
              .edge-wg {{
                animation: dash-flow 1.5s linear infinite;
              }}
            </style>
          </defs>

          <!-- Draw edges first (behind nodes) -->
          {#each topology.edges as edge (edge.id)}
            {@const from = nodeCenter(edge.from)}
            {@const to = nodeCenter(edge.to)}
            {@const isReverse = edge.from > edge.to}
            {@const hasReverse = hasReverseEdge(edge)}
            {@const offset = offsetLine(from.x, from.y, to.x, to.y, isReverse)}
            {#if edge.type === 'wireguard'}
              <line
                x1={hasReverse ? offset.x1 : from.x}
                y1={hasReverse ? offset.y1 : from.y}
                x2={hasReverse ? offset.x2 : to.x}
                y2={hasReverse ? offset.y2 : to.y}
                stroke="var(--accent)"
                stroke-width="1.5"
                stroke-dasharray="6,3"
                class="edge-wg"
                opacity={hoveredEdge === edge.id ? 1 : 0.5}
                role="presentation"
                onmouseenter={() => (hoveredEdge = edge.id)}
                onmouseleave={() => (hoveredEdge = null)}
              />
            {:else if edge.type === 'autossh'}
              <line
                x1={hasReverse ? offset.x1 : from.x}
                y1={hasReverse ? offset.y1 : from.y}
                x2={hasReverse ? offset.x2 : to.x}
                y2={hasReverse ? offset.y2 : to.y}
                stroke="var(--running)"
                stroke-width="1"
                stroke-dasharray="4,4"
                marker-end="url(#arrowhead-autossh)"
                opacity={hoveredEdge === edge.id ? 1 : 0.5}
                role="presentation"
                onmouseenter={() => (hoveredEdge = edge.id)}
                onmouseleave={() => (hoveredEdge = null)}
              />
            {/if}
          {/each}

          <!-- Draw nodes -->
          {#each topology.nodes as node, idx (node.id)}
            {@const pos = layout[node.id] || { x: 0, y: 0 }}
            <g
              class="node"
              class:selected={selectedNode === node.id}
              role="button"
              tabindex="0"
              onclick={() => (selectedNode = selectedNode === node.id ? null : node.id)}
              onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (selectedNode = selectedNode === node.id ? null : node.id)}
              style="animation-delay: {idx * 80}ms;"
            >
              <!-- OS stripe (left accent) -->
              <rect
                x={pos.x}
                y={pos.y}
                width="4"
                height="44"
                fill={node.os === 'OpenBSD'
                  ? OS_COLORS.openbsd
                  : node.os === 'FreeBSD'
                    ? OS_COLORS.freebsd
                    : node.os === 'Linux'
                      ? OS_COLORS.linux
                      : '#555'}
                rx="1"
              />

              <!-- Card background -->
              <rect x={pos.x + 4} y={pos.y} width="126" height="44" fill="var(--bg-2)" stroke="var(--border)" stroke-width="1" rx="2" />

              <!-- Hostname -->
              <text x={pos.x + 69} y={pos.y + 15} class="node-label">
                {node.id.length > 14 ? node.id.slice(0, 13) + '…' : node.id}
              </text>

              <!-- Location -->
              <text x={pos.x + 69} y={pos.y + 32} class="node-loc">{node.location || '?'}</text>

              <!-- Status dot -->
              <circle cx={pos.x + 122} cy={pos.y + 7} r="3" fill={node.wg_interfaces ? 'var(--accent)' : '#555'} />
            </g>
          {/each}
        </svg>
      {/if}
    </div>
  </div>

  {#if selectedNode && topology}
    <div class="detail-panel">
      <div class="detail-header">
        <h3>{selectedNode}</h3>
        <button class="close" onclick={() => (selectedNode = null)}>×</button>
      </div>
      <div class="detail-content">
        {#if topology.nodes.find(n => n.id === selectedNode)?.wg_interfaces}
          {@const node = topology.nodes.find(n => n.id === selectedNode)}
          <div class="section">
            <h4>WireGuard Interfaces</h4>
            {#each Object.entries(node.wg_interfaces || {}) as [iface, addr]}
              <div class="iface-row">
                <span class="iface-name">{iface}</span>
                <span class="iface-addr">{addr}</span>
              </div>
            {/each}
          </div>
        {/if}

        <div class="section">
          <h4>Connected Peers</h4>
          {#each getSelectedNodePeers() as peer}
            {@const edges = topology.edges.filter(e => (e.from === selectedNode && e.to === peer) || (e.from === peer && e.to === selectedNode))}
            <div class="peer-row">
              <span class="peer-name">{peer}</span>
              {#each edges as edge}
                <span class="edge-type {edge.type}">{edge.interface || edge.type}</span>
              {/each}
            </div>
          {/each}
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .container {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg);
    color: var(--text);
    font-family: var(--ui);
  }

  .header {
    padding: 20px 28px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(90deg, var(--bg-2) 0%, rgba(15, 22, 41, 0.5) 100%);
  }

  .title {
    font-size: clamp(10px, 1.6vw, 11px);
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .controls {
    display: flex;
    gap: 8px;
  }

  .controls button {
    padding: 10px 12px;
    background: var(--bg-2);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
    transition: all 150ms;
    min-height: 44px;
  }

  .controls button:hover:not(.loading):not(:disabled) {
    background: var(--bg-3);
    border-color: var(--accent);
  }

  .controls button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .controls button.loading {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .main {
    display: grid;
    grid-template-columns: 200px 1fr;
    flex: 1;
    overflow: hidden;
  }

  .sidebar {
    border-right: 1px solid var(--border);
    padding: 16px 12px;
    overflow-y: auto;
    background: var(--bg);
  }

  .section {
    margin-bottom: 20px;
  }

  .section h3 {
    margin: 0 0 10px 0;
    font-size: clamp(11px, 2vw, 12px);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
  }

  .section h4 {
    margin: 0 0 8px 0;
    font-size: clamp(12px, 2.2vw, 13px);
    font-weight: 700;
    color: var(--text);
    font-family: var(--ui);
  }

  .location-item {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
    font-size: clamp(12px, 2.2vw, 13px);
    font-family: var(--ui);
  }

  .location-item .dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .location-item .loc-name {
    flex: 1;
  }

  .location-item .count {
    color: var(--text-muted);
    font-size: clamp(10px, 1.8vw, 11px);
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
    font-size: clamp(12px, 2.2vw, 13px);
    font-family: var(--ui);
  }

  .selected-info {
    background: var(--bg-2);
    padding: 10px;
    border-radius: 4px;
    border-left: 3px solid var(--accent);
  }

  .selected-info h3 {
    margin-bottom: 6px;
    text-transform: none;
    letter-spacing: normal;
    color: var(--text);
  }

  .info-text {
    margin: 0;
    font-size: clamp(12px, 2.2vw, 13px);
    color: var(--text-muted);
    font-family: var(--ui);
  }

  .peer-count {
    color: var(--accent);
    font-weight: 600;
  }

  .diagram-container {
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: auto;
    background: var(--bg-2);
    position: relative;
  }

  .loading,
  .error {
    font-size: 14px;
    color: var(--text-muted);
    text-align: center;
  }

  .error {
    color: var(--error);
  }

  .diagram {
    width: 100%;
    max-width: 700px;
    height: auto;
    background: var(--bg-2);
    filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.3));
  }

  .node {
    cursor: pointer;
    transition: all 150ms;
    animation: fade-in 0.4s ease-out forwards;
    opacity: 0;
  }

  @keyframes fade-in {
    from {
      opacity: 0;
      transform: translate(0, 10px);
    }
    to {
      opacity: 1;
      transform: translate(0, 0);
    }
  }

  .node:hover rect:nth-of-type(2) {
    stroke: var(--accent);
    stroke-width: 1.5;
  }

  .node.selected rect:nth-of-type(2) {
    stroke: var(--accent);
    stroke-width: 2;
    filter: drop-shadow(0 0 6px rgba(0, 212, 170, 0.4));
  }

  .node-label {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    fill: var(--text);
    text-anchor: middle;
    pointer-events: none;
  }

  .node-loc {
    font-family: var(--mono);
    font-size: 9px;
    fill: var(--text-dim);
    text-anchor: middle;
    pointer-events: none;
  }

  .detail-panel {
    position: absolute;
    bottom: 0;
    left: 200px;
    right: 0;
    background: var(--bg-2);
    border-top: 1px solid var(--border);
    max-height: 200px;
    overflow-y: auto;
    animation: slide-up 0.3s ease-out;
  }

  @keyframes slide-up {
    from {
      transform: translateY(100%);
    }
    to {
      transform: translateY(0);
    }
  }

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
  }

  .detail-header h3 {
    margin: 0;
    font-family: var(--ui);
    font-size: clamp(13px, 2.8vw, 15px);
    font-weight: 700;
    color: var(--accent);
  }

  .detail-header .close {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 20px;
    cursor: pointer;
    padding: 0 8px;
    transition: color 150ms;
    min-height: 44px;
    min-width: 44px;
  }

  .detail-header .close:hover {
    color: var(--text);
  }

  .detail-content {
    padding: 12px 16px;
    display: flex;
    gap: 24px;
  }

  .detail-content .section {
    flex: 1;
    margin-bottom: 0;
  }

  .iface-row {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
    font-size: clamp(11px, 2vw, 12px);
  }

  .iface-name {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: clamp(10px, 1.8vw, 11px);
  }

  .iface-addr {
    color: var(--accent);
    font-family: var(--mono);
    font-size: clamp(10px, 1.8vw, 11px);
    font-weight: 600;
  }

  .peer-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: clamp(11px, 2vw, 12px);
  }

  .peer-name {
    color: var(--text);
    font-family: var(--mono);
    font-size: 11px;
  }

  .edge-type {
    display: inline-block;
    padding: 2px 6px;
    background: var(--bg-3);
    border-radius: 2px;
    font-size: 10px;
    color: var(--text-muted);
  }

  .edge-type.wireguard {
    border-left: 2px solid var(--accent);
    color: var(--accent);
  }

  .edge-type.autossh {
    border-left: 2px solid var(--running);
    color: var(--running);
  }

  @media (max-width: 900px) {
    .header {
      padding: clamp(8px, 1.2vw, 12px) clamp(12px, 1.5vw, 16px);
      gap: 8px;
    }

    .controls button {
      font-size: clamp(11px, 1.2vw, 13px);
      padding: clamp(4px, 0.6vw, 6px) clamp(6px, 1vw, 8px);
    }

    .sidebar {
      padding: clamp(8px, 1.2vw, 12px);
      width: 180px;
    }

    .section h3 {
      font-size: clamp(9px, 1.2vw, 11px);
    }

    .location-item,
    .legend-item {
      font-size: clamp(11px, 1.3vw, 12px);
    }

    .diagram {
      max-width: 95vw;
      height: auto;
    }
  }

  @media (max-width: 768px) {
    .container {
      height: auto;
    }

    .main {
      grid-template-columns: 1fr;
      grid-template-rows: auto auto;
    }

    .header {
      padding: clamp(8px, 1.2vw, 10px) clamp(12px, 1.5vw, 14px);
      flex-direction: column;
      gap: 6px;
    }

    .controls {
      width: 100%;
      gap: 6px;
    }

    .controls button {
      flex: 1;
      font-size: clamp(10px, 1.1vw, 11px);
      padding: clamp(4px, 0.8vw, 6px);
    }

    .sidebar {
      border-right: none;
      border-top: 1px solid var(--border);
      max-height: 160px;
      padding: clamp(8px, 1.2vw, 10px);
      width: 100%;
    }

    .diagram-container {
      order: -1;
      min-height: 200px;
      align-items: flex-start;
      padding: 8px 4px;
    }

    .diagram {
      max-width: 98vw;
      width: 98vw;
      height: auto;
    }

    .detail-panel {
      left: 0;
      max-height: 180px;
    }

    .section h3 {
      font-size: clamp(9px, 1.1vw, 10px);
      margin-bottom: 8px;
    }

    .location-item,
    .legend-item {
      font-size: clamp(10px, 1vw, 11px);
    }

    .iface-name,
    .peer-name {
      font-size: clamp(10px, 1.1vw, 11px);
    }
  }

  @media (max-width: 640px) {
    .container {
      height: auto;
    }

    .header {
      padding: clamp(6px, 1vw, 8px) clamp(8px, 1.2vw, 10px);
      gap: 4px;
    }

    .controls {
      width: 100%;
      gap: 4px;
    }

    .controls button {
      flex: 1;
      font-size: clamp(10px, 1vw, 11px);
      padding: clamp(4px, 0.6vw, 5px) clamp(4px, 0.8vw, 6px);
    }

    .main {
      grid-template-columns: 1fr;
    }

    .sidebar {
      max-height: 140px;
      padding: clamp(6px, 1vw, 8px);
    }

    .diagram-container {
      min-height: 220px;
      overflow-x: auto;
      overflow-y: hidden;
    }

    .diagram {
      min-width: 600px;
      width: auto;
      height: auto;
    }

    .section h3 {
      font-size: clamp(8px, 1vw, 9px);
      margin-bottom: 6px;
    }

    .location-item,
    .legend-item {
      font-size: clamp(10px, 0.9vw, 11px);
      margin-bottom: clamp(4px, 0.8vw, 5px);
    }

    .detail-panel {
      max-height: 160px;
      font-size: clamp(10px, 0.9vw, 11px);
    }

    .detail-header h3 {
      font-size: clamp(11px, 1vw, 12px);
    }

    .iface-name,
    .peer-name {
      font-size: clamp(9px, 0.9vw, 10px);
    }

    .edge-type {
      font-size: clamp(8px, 0.8vw, 9px);
      padding: 1px 4px;
    }
  }

  @media (max-width: 480px) {
    .header {
      padding: 6px 8px;
    }

    .controls button {
      font-size: 10px;
      padding: 4px 6px;
    }

    .sidebar {
      max-height: 120px;
      padding: 6px 8px;
    }

    .diagram {
      min-width: 500px;
    }

    .section h3 {
      font-size: 8px;
      margin-bottom: 4px;
    }

    .location-item,
    .legend-item {
      font-size: 10px;
      margin-bottom: 3px;
    }

    .detail-panel {
      max-height: 140px;
    }

    .detail-header h3 {
      font-size: 11px;
    }

    .iface-name,
    .peer-name {
      font-size: 9px;
    }

    .edge-type {
      font-size: 8px;
      padding: 1px 3px;
    }
  }
</style>
