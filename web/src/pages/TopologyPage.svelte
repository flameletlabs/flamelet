<script>
  import { onMount } from 'svelte';
  import { getTopology, getTenants } from '../lib/api.js';

  let tenants = [];
  let selectedTenant = null;
  let topology = null;
  let selectedNode = null;
  let hoveredEdge = null;
  let loading = false;
  let error = null;

  const nodePositions = {
    'core.home': { x: 400, y: 180 },
    'virt.home': { x: 120, y: 280 },
    'controller.work': { x: 220, y: 420 },
    'virt-01.baar': { x: 680, y: 80 },
    'virt-02.baar': { x: 700, y: 140 },
    'virt-03.baar': { x: 680, y: 200 },
    'nas-01.pangea': { x: 80, y: 80 },
    'wg.floads.io': { x: 680, y: 340 },
  };

  const osColors = {
    openbsd: '#e3b341',
    freebsd: '#cd7b6a',
    linux: '#4493f8',
  };

  onMount(async () => {
    tenants = await getTenants();
    if (tenants.length > 0) {
      selectedTenant = tenants[0].name;
      loadTopology();
    }
  });

  async function loadTopology() {
    loading = true;
    error = null;
    try {
      topology = await getTopology(selectedTenant);
      selectedNode = null;
    } catch (e) {
      error = e.message;
    }
    loading = false;
  }

  function getNodePosition(hostname) {
    return nodePositions[hostname] || { x: Math.random() * 600 + 50, y: Math.random() * 400 + 50 };
  }

  function getOSColor(hostname) {
    // Infer OS from hostname or config
    if (hostname.includes('openbsd') || hostname === 'core.home' || hostname === 'controller.work') {
      return osColors.openbsd;
    }
    if (hostname.includes('freebsd') || hostname.includes('virt') || hostname.includes('nas')) {
      return osColors.freebsd;
    }
    if (hostname.includes('docker') || hostname.includes('k3s') || hostname.includes('dev')) {
      return osColors.linux;
    }
    return '#666';
  }

  function formatIP(addr) {
    return addr ? addr.split('/')[0] : '?';
  }

  function getSelectedNodePeers() {
    if (!selectedNode || !topology) return [];
    const edges = topology.edges.filter(e => e.from === selectedNode || e.to === selectedNode);
    const peers = new Set();
    edges.forEach(e => {
      if (e.from === selectedNode) peers.add(e.to);
      else peers.add(e.from);
    });
    return Array.from(peers).sort();
  }
</script>

<div class="container">
  <div class="header">
    <h1>Network Topology</h1>
    <div class="controls">
      <select bind:value={selectedTenant} on:change={loadTopology}>
        <option value="">— Select Tenant —</option>
        {#each tenants as tenant}
          <option value={tenant.name}>{tenant.name}</option>
        {/each}
      </select>
      <button on:click={loadTopology} class:loading>
        {loading ? '⟳' : '↺'} Refresh
      </button>
    </div>
  </div>

  <div class="main">
    <div class="sidebar">
      <div class="section">
        <h3>Locations</h3>
        {#if topology}
          {#each Object.keys(topology.locations).sort() as location}
            <label class="location-item">
              <input type="checkbox" />
              <span class="dot" style="background: var(--accent);"></span>
              {location}
              <span class="count">{topology.locations[location].length}</span>
            </label>
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
        <svg viewBox="0 0 800 500" class="diagram">
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
            {#if edge.type === 'wireguard'}
              {@const fromPos = getNodePosition(edge.from)}
              {@const toPos = getNodePosition(edge.to)}
              <line
                x1={fromPos.x + 60}
                y1={fromPos.y + 25}
                x2={toPos.x + 60}
                y2={toPos.y + 25}
                stroke="var(--accent)"
                stroke-width="1.5"
                stroke-dasharray="6,3"
                class="edge-wg"
                opacity={hoveredEdge === edge.id ? 1 : 0.6}
                on:mouseenter={() => (hoveredEdge = edge.id)}
                on:mouseleave={() => (hoveredEdge = null)}
              />
            {:else if edge.type === 'autossh'}
              {@const fromPos = getNodePosition(edge.from)}
              {@const toPos = getNodePosition(edge.to)}
              <line
                x1={fromPos.x + 60}
                y1={fromPos.y + 25}
                x2={toPos.x + 60}
                y2={toPos.y + 25}
                stroke="var(--running)"
                stroke-width="1"
                stroke-dasharray="4,4"
                marker-end="url(#arrowhead-autossh)"
                opacity={hoveredEdge === edge.id ? 1 : 0.5}
                on:mouseenter={() => (hoveredEdge = edge.id)}
                on:mouseleave={() => (hoveredEdge = null)}
              />
            {/if}
          {/each}

          <!-- Draw nodes -->
          {#each topology.nodes as node, idx (node.id)}
            {@const pos = getNodePosition(node.id)}
            <g
              class="node"
              class:selected={selectedNode === node.id}
              on:click={() => (selectedNode = node.id)}
              style="animation-delay: {idx * 80}ms;"
            >
              <!-- Accent bar -->
              <rect x={pos.x} y={pos.y} width="3" height="50" fill={getOSColor(node.id)} rx="1" />

              <!-- Main rect -->
              <rect x={pos.x + 3} y={pos.y} width="117" height="50" fill="var(--bg-2)" stroke="var(--border)" stroke-width="1" rx="2" />

              <!-- Hostname -->
              <text x={pos.x + 63} y={pos.y + 16} class="node-label">{node.id}</text>

              <!-- IP address -->
              {#if node.wg_interfaces && Object.keys(node.wg_interfaces).length > 0}
                {@const firstIp = formatIP(Object.values(node.wg_interfaces)[0])}
                <text x={pos.x + 63} y={pos.y + 36} class="node-ip">{firstIp}</text>
              {/if}

              <!-- Status dot -->
              <circle cx={pos.x + 115} cy={pos.y + 5} r="3" fill={node.wg_interfaces ? 'var(--accent)' : '#555'} />
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
        <button class="close" on:click={() => (selectedNode = null)}>×</button>
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
    height: 100vh;
    background: var(--bg);
    color: var(--text);
    font-family: var(--ui);
  }

  .header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    letter-spacing: -0.3px;
  }

  .controls {
    display: flex;
    gap: 8px;
  }

  .controls select {
    padding: 6px 8px;
    background: var(--bg-2);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 4px;
    font-size: 13px;
    font-family: var(--ui);
    cursor: pointer;
  }

  .controls button {
    padding: 6px 12px;
    background: var(--bg-2);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
    transition: all 150ms;
  }

  .controls button:hover:not(.loading) {
    background: var(--bg-3);
    border-color: var(--accent);
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
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
  }

  .section h4 {
    margin: 0 0 8px 0;
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
  }

  .location-item {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
    font-size: 12px;
    cursor: pointer;
  }

  .location-item input {
    width: 14px;
    height: 14px;
    cursor: pointer;
  }

  .location-item .dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .location-item .count {
    margin-left: auto;
    color: var(--text-muted);
    font-size: 11px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
    font-size: 12px;
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
    font-size: 12px;
    color: var(--text-muted);
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
    max-width: 900px;
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
    font-size: 10px;
    font-weight: 600;
    fill: var(--text);
    text-anchor: middle;
    pointer-events: none;
  }

  .node-ip {
    font-family: var(--mono);
    font-size: 8px;
    fill: var(--text-muted);
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
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 600;
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
    font-size: 12px;
  }

  .iface-name {
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 11px;
  }

  .iface-addr {
    color: var(--accent);
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 600;
  }

  .peer-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 12px;
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
    }

    .title {
      font-size: clamp(10px, 1.4vw, 12px);
    }

    .tenant-select {
      font-size: clamp(10px, 1.2vw, 11px);
    }

    svg {
      width: 100%;
      height: clamp(300px, 60vh, 500px);
    }

    .sidebar {
      padding: clamp(8px, 1.2vw, 12px);
    }

    .node-detail-title {
      font-size: clamp(11px, 1.4vw, 12px);
    }

    .iface-name, .peer-name {
      font-size: clamp(9px, 1.2vw, 10px);
    }
  }

  @media (max-width: 768px) {
    .layout {
      grid-template-columns: 1fr;
      grid-template-rows: auto 1fr auto;
    }

    .header {
      padding: clamp(8px, 1.2vw, 10px);
    }

    .title {
      font-size: clamp(10px, 1.3vw, 11px);
    }

    .tenant-select {
      font-size: clamp(9px, 1vw, 10px);
      padding: clamp(3px, 0.6vw, 5px) clamp(6px, 1vw, 8px);
    }

    svg {
      height: clamp(250px, 50vh, 400px);
      margin: clamp(8px, 1.2vw, 10px);
      border: 1px solid var(--border);
      border-radius: 3px;
    }

    .sidebar {
      max-height: 200px;
      border-top: 1px solid var(--border);
      border-right: none;
      padding: clamp(8px, 1.2vw, 10px);
      overflow-y: auto;
    }

    .node-detail-title {
      font-size: clamp(10px, 1.2vw, 11px);
      margin-bottom: 4px;
    }

    .iface-section, .edges-section {
      margin-bottom: clamp(8px, 1vw, 10px);
    }

    .iface-addr {
      font-size: clamp(9px, 1.1vw, 10px);
    }
  }

  @media (max-width: 640px) {
    .header {
      flex-direction: column;
      gap: clamp(6px, 1vw, 8px);
      padding: clamp(6px, 1vw, 8px);
    }

    .tenant-select {
      width: 100%;
    }

    svg {
      height: clamp(200px, 40vh, 300px);
      margin: clamp(6px, 1vw, 8px);
    }

    .sidebar {
      max-height: 150px;
    }

    .node-detail-title {
      font-size: clamp(10px, 1.2vw, 11px);
    }

    .iface-name, .peer-name {
      font-size: clamp(8px, 1vw, 9px);
    }

    .edge-type {
      font-size: 8px;
      padding: 1px 4px;
    }
  }

  @media (max-width: 480px) {
    svg {
      height: clamp(150px, 35vh, 250px);
    }

    .sidebar {
      max-height: 120px;
    }

    .node-detail-title {
      font-size: 10px;
    }

    .iface-name {
      font-size: 8px;
    }

    .peer-name {
      font-size: 8px;
    }
  }
</style>
