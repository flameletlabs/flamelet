<script>
  import { onMount } from 'svelte';
  import { getTopology, getTenants } from '../lib/api.js';

  let tenants = $state([]);
  let selectedTenant = $state(null);
  let topology = $state(null);
  let selectedNode = $state(null);
  let hoveredEdge = $state(null);
  let loading = $state(false);
  let error = $state(null);

  const nodePositions = {
    'fw.example.com': { x: 400, y: 180 },
    'virt.example.com': { x: 120, y: 280 },
    'controller.example.com': { x: 220, y: 420 },
    'virt-01.example.com': { x: 680, y: 80 },
    'virt-02.example.com': { x: 700, y: 140 },
    'virt-03.example.com': { x: 680, y: 200 },
    'nas.example.com': { x: 80, y: 80 },
    'vpn.example.com': { x: 680, y: 340 },
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
    if (hostname.includes('openbsd') || hostname.includes('fw') || hostname.includes('controller')) {
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
      <select bind:value={selectedTenant} onchange={loadTopology}>
        <option value="">— Select Tenant —</option>
        {#each tenants as tenant}
          <option value={tenant.name}>{tenant.name}</option>
        {/each}
      </select>
      <button onclick={loadTopology} class:loading>
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
                role="presentation"
                onmouseenter={() => (hoveredEdge = edge.id)}
                onmouseleave={() => (hoveredEdge = null)}
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
                role="presentation"
                onmouseenter={() => (hoveredEdge = edge.id)}
                onmouseleave={() => (hoveredEdge = null)}
              />
            {/if}
          {/each}

          <!-- Draw nodes -->
          {#each topology.nodes as node, idx (node.id)}
            {@const pos = getNodePosition(node.id)}
            <g
              class="node"
              class:selected={selectedNode === node.id}
              role="button"
              tabindex="0"
              onclick={() => (selectedNode = node.id)}
              onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (selectedNode = node.id)}
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

  .header h1 {
    margin: 0;
    font-size: clamp(18px, 4vw, 20px);
    font-weight: 600;
    letter-spacing: -0.3px;
    font-family: var(--ui);
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
    cursor: pointer;
    font-family: var(--ui);
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
    font-size: clamp(10px, 1.8vw, 11px);
    font-weight: 700;
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

    .header h1 {
      font-size: clamp(16px, 2vw, 20px);
    }

    .controls select,
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
    .main {
      grid-template-columns: 1fr;
      grid-template-rows: 1fr auto;
    }

    .header {
      padding: clamp(8px, 1.2vw, 10px) clamp(12px, 1.5vw, 14px);
      flex-direction: column;
      gap: 6px;
    }

    .header h1 {
      font-size: clamp(14px, 1.8vw, 18px);
      margin: 0;
    }

    .controls {
      width: 100%;
      gap: 6px;
    }

    .controls select,
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
      min-height: 220px;
      max-height: 55vh;
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
      height: 100%;
    }

    .header {
      padding: clamp(6px, 1vw, 8px) clamp(8px, 1.2vw, 10px);
      gap: 4px;
    }

    .header h1 {
      font-size: clamp(13px, 1.6vw, 16px);
    }

    .controls {
      width: 100%;
      gap: 4px;
    }

    .controls select,
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

    .header h1 {
      font-size: 13px;
    }

    .controls select,
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
