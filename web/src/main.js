import './app.css'

const appDiv = document.getElementById('app')
let currentPage = 'dashboard'
let topologyData = null

const nodePositions = {
  'core.home': { x: 400, y: 180 },
  'virt.home': { x: 120, y: 280 },
  'controller.work': { x: 220, y: 420 },
  'virt-01.baar': { x: 680, y: 80 },
  'nas-01.pangea': { x: 80, y: 80 },
}

function getOSColor(hostname) {
  if (hostname.includes('openbsd') || hostname === 'core.home' || hostname === 'controller.work') return '#e3b341'
  if (hostname.includes('freebsd') || hostname.includes('virt') || hostname.includes('nas')) return '#cd7b6a'
  if (hostname.includes('docker') || hostname.includes('k3s')) return '#4493f8'
  return '#666'
}

async function loadTenants() {
  try {
    const res = await fetch('/api/tenants')
    return await res.json()
  } catch (e) {
    console.error('Error loading tenants:', e)
    return []
  }
}

async function renderApp() {
  const tenants = await loadTenants()

  const dashboardPage = `
    <div style="padding: 20px; color: var(--text);">
      <h1 style="color: var(--accent); margin: 0 0 10px 0; font-size: 28px;">Dashboard</h1>
      <p style="color: var(--text-muted); margin: 0 0 20px 0;">Welcome to Flamelet infrastructure management</p>

      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px;">
        ${tenants.map(tenant => `
          <div style="background: var(--bg-2); border: 1px solid var(--border); padding: 16px; border-radius: 4px; cursor: pointer; transition: all 150ms;" onmouseover="this.style.borderColor='var(--accent)';this.style.background='var(--bg-3)'" onmouseout="this.style.borderColor='var(--border)';this.style.background='var(--bg-2)'">
            <h3 style="color: var(--accent); margin: 0; font-size: 16px;">${tenant.name}</h3>
            <p style="color: var(--text-muted); margin: 8px 0 0 0; font-size: 14px;">${tenant.host_count} hosts</p>
          </div>
        `).join('')}
      </div>
    </div>
  `

  const loadingPage = `
    <div style="padding: 20px; color: var(--text-muted);">Loading topology...</div>
  `

  const topologyPage = topologyData ? `
    <div style="display: grid; grid-template-columns: 200px 1fr; flex: 1; overflow: hidden; height: 100%;">
      <div style="border-right: 1px solid var(--border); padding: 16px 12px; overflow-y: auto; background: var(--bg);">
        <h3 style="margin: 0 0 10px 0; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-muted);">Locations</h3>
        ${Object.keys(topologyData.locations || {}).sort().map(loc => `
          <div style="margin-bottom: 6px; font-size: 12px; color: var(--text);">
            <span style="color: var(--accent);">●</span> ${loc}
            <span style="color: var(--text-muted); float: right;">${topologyData.locations[loc].length}</span>
          </div>
        `).join('')}

        <h3 style="margin: 20px 0 10px 0; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-muted);">Legend</h3>
        <div style="font-size: 12px; margin-bottom: 8px; color: var(--text);">
          <span style="color: var(--accent);">——</span> WireGuard
        </div>
        <div style="font-size: 12px; margin-bottom: 8px; color: var(--text);">
          <span style="color: var(--running);">╌╌</span> AutoSSH
        </div>
      </div>
      <div style="overflow: auto; background: var(--bg-2); display: flex; align-items: center; justify-content: center;">
        <svg viewBox="0 0 800 500" style="width: 100%; max-width: 900px; height: auto; padding: 20px;">
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <polygon points="0 0, 10 3, 0 6" fill="var(--running)" />
            </marker>
            <style>
              @keyframes dash { to { stroke-dashoffset: -18; } }
              .wg-edge { animation: dash 1.5s linear infinite; stroke: var(--accent); stroke-width: 1.5; stroke-dasharray: 6,3; }
              .ssh-edge { stroke: var(--running); stroke-width: 1; stroke-dasharray: 4,4; }
            </style>
          </defs>

          ${(topologyData.edges || []).map(edge => {
            const fromPos = nodePositions[edge.from] || { x: 200, y: 200 }
            const toPos = nodePositions[edge.to] || { x: 600, y: 300 }
            const cls = edge.type === 'wireguard' ? 'wg-edge' : 'ssh-edge'
            const marker = edge.type === 'autossh' ? ' marker-end="url(#arrowhead)"' : ''
            return `<line x1="${fromPos.x + 60}" y1="${fromPos.y + 25}" x2="${toPos.x + 60}" y2="${toPos.y + 25}" class="${cls}" opacity="0.6"${marker} />`
          }).join('')}

          ${(topologyData.nodes || []).map((node, idx) => {
            const pos = nodePositions[node.id] || { x: Math.random() * 600 + 50, y: Math.random() * 400 + 50 }
            const color = getOSColor(node.id)
            const ip = node.wg_interfaces ? Object.values(node.wg_interfaces)[0]?.split('/')[0] : '?'
            return `
              <g style="cursor: pointer;">
                <rect x="${pos.x}" y="${pos.y}" width="3" height="50" fill="${color}" rx="1" />
                <rect x="${pos.x + 3}" y="${pos.y}" width="117" height="50" fill="var(--bg-2)" stroke="var(--border)" stroke-width="1" rx="2" />
                <text x="${pos.x + 63}" y="${pos.y + 16}" font-family="var(--mono)" font-size="10" font-weight="600" fill="var(--text)" text-anchor="middle">${node.id}</text>
                <text x="${pos.x + 63}" y="${pos.y + 36}" font-family="var(--mono)" font-size="8" fill="var(--text-muted)" text-anchor="middle">${ip}</text>
              </g>
            `
          }).join('')}
        </svg>
      </div>
    </div>
  ` : loadingPage

  appDiv.innerHTML = `
    <div class="app-wrapper">
      <nav class="top-nav">
        <div class="nav-brand">Flamelet</div>
        <div class="nav-links">
          <button class="${currentPage === 'dashboard' ? 'active' : ''}" onclick="window.setPage('dashboard')" style="padding: 6px 12px; background: ${currentPage === 'dashboard' ? 'rgba(0, 212, 170, 0.08)' : 'transparent'}; border: 1px solid ${currentPage === 'dashboard' ? '#00d4aa' : 'transparent'}; color: ${currentPage === 'dashboard' ? '#00d4aa' : '#7d8590'}; font-size: 13px; cursor: pointer; border-radius: 4px; transition: all 150ms;">Dashboard</button>
          <button class="${currentPage === 'topology' ? 'active' : ''}" onclick="window.setPage('topology')" style="padding: 6px 12px; background: ${currentPage === 'topology' ? 'rgba(0, 212, 170, 0.08)' : 'transparent'}; border: 1px solid ${currentPage === 'topology' ? '#00d4aa' : 'transparent'}; color: ${currentPage === 'topology' ? '#00d4aa' : '#7d8590'}; font-size: 13px; cursor: pointer; border-radius: 4px; transition: all 150ms;">Topology</button>
        </div>
      </nav>
      <div class="page-container">
        ${currentPage === 'dashboard' ? dashboardPage : topologyPage}
      </div>
    </div>
  `
}

window.setPage = (page) => {
  currentPage = page
  if (page === 'topology' && !topologyData) {
    fetch('/api/tenants/flamelet-home/topology')
      .then(r => r.json())
      .then(data => {
        topologyData = data
        renderApp()
      })
      .catch(e => console.error('API error:', e))
  }
  renderApp()
}

renderApp()
