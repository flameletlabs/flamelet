<script>
  import { getLocations, getTenantHosts } from '../lib/api.js'
  import L from 'leaflet'
  import 'leaflet/dist/leaflet.css'

  let { tenant = null } = $props()

  let mapInstance = $state(null)
  let locations = $state([])
  let allHosts = $state([])
  let selectedHost = $state(null)
  let loading = $state(true)
  let error = $state(null)
  let locationsWithoutCoords = $state([])
  let zoomLevel = $state(4)

  // Layer groups
  let locationLayer = null
  let hostLayer = null

  const OS_COLORS = {
    OpenBSD: '#e3b341',
    FreeBSD: '#cd7b6a',
    Linux: '#4493f8',
  }

  const ZOOM_THRESHOLD = 10

  async function loadMap() {
    if (!tenant) return
    loading = true
    error = null

    try {
      // Load locations and hosts in parallel
      const [locs, hosts] = await Promise.all([
        getLocations(tenant),
        getTenantHosts(tenant),
      ])

      locations = locs
      allHosts = hosts

      if (!mapInstance) {
        initMap()
      }

      buildLayers(locations)
    } catch (e) {
      error = e.message
      console.error('Failed to load map:', e)
    } finally {
      loading = false
    }
  }

  function initMap() {
    if (mapInstance) return
    mapInstance = L.map('leaflet-map').setView([48, 10], 4)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(mapInstance)

    // Zoom event listener
    mapInstance.on('zoomend', applyZoomLayers)
  }

  function buildLayers(locs) {
    if (!mapInstance) return

    // Clear old layers
    if (locationLayer) locationLayer.clearLayers()
    else locationLayer = L.layerGroup()

    if (hostLayer) hostLayer.clearLayers()
    else hostLayer = L.layerGroup()

    const mappedLocs = locs.filter(l => l.lat && l.lon)
    locationsWithoutCoords = locs.filter(l => !l.lat || !l.lon)

    // Create host map for quick lookup
    const hostMap = Object.fromEntries(allHosts.map(h => [h.name, h]))

    mappedLocs.forEach(loc => {
      // --- Location marker (overview, zoom < ZOOM_THRESHOLD) ---
      const locMarker = L.marker([loc.lat, loc.lon], {
        icon: createLocationIcon(loc),
        zIndexOffset: 100,
      }).on('click', () => {
        mapInstance.flyTo([loc.lat, loc.lon], ZOOM_THRESHOLD + 1, { duration: 0.8 })
      })
      locationLayer.addLayer(locMarker)

      // --- Host markers (detail, zoom >= ZOOM_THRESHOLD) ---
      const count = loc.hosts.length
      loc.hosts.forEach((host, i) => {
        const [lat, lon] = count > 1 ? spreadPosition(loc.lat, loc.lon, i, count) : [loc.lat, loc.lon]

        const hostMarker = L.marker([lat, lon], {
          icon: createHostIcon(host),
        }).on('click', () => {
          // Merge location data with full host details
          const fullHost = hostMap[host.name] || host
          selectedHost = { ...fullHost, display_name: loc.display_name }
        })
        hostLayer.addLayer(hostMarker)
      })
    })

    // Render correct layer for current zoom
    applyZoomLayers()

    // Fit bounds to all mapped locations
    if (mappedLocs.length > 0) {
      const bounds = L.latLngBounds(mappedLocs.map(l => [l.lat, l.lon]))
      setTimeout(() => mapInstance.fitBounds(bounds, { padding: [50, 50] }), 100)
    }
  }

  function spreadPosition(lat, lon, index, total) {
    const radiusDeg = 0.008 // ~800m radius at mid-latitudes
    const angle = (index / total) * 2 * Math.PI - Math.PI / 2
    return [lat + radiusDeg * Math.sin(angle), lon + radiusDeg * Math.cos(angle) * 1.4]
  }

  function applyZoomLayers() {
    if (!mapInstance || !locationLayer || !hostLayer) return
    const zoom = mapInstance.getZoom()
    zoomLevel = zoom
    if (zoom >= ZOOM_THRESHOLD) {
      if (!mapInstance.hasLayer(hostLayer)) hostLayer.addTo(mapInstance)
      if (mapInstance.hasLayer(locationLayer)) locationLayer.remove()
    } else {
      if (!mapInstance.hasLayer(locationLayer)) locationLayer.addTo(mapInstance)
      if (mapInstance.hasLayer(hostLayer)) hostLayer.remove()
    }
  }

  function createLocationIcon(loc) {
    const os = loc.hosts.map(h => h.os)
    const dominant = ['OpenBSD', 'FreeBSD', 'Linux'].find(o => os.includes(o)) || null
    const ring = dominant ? OS_COLORS[dominant] : 'var(--accent)'

    return L.divIcon({
      className: '',
      html: `
        <div class="loc-pin" style="--ring: ${ring}">
          <span class="loc-pin-name">${loc.name}</span>
          <span class="loc-pin-count">${loc.host_count}</span>
        </div>`,
      iconSize: [null, null],
      iconAnchor: [0, 0],
    })
  }

  function createHostIcon(host) {
    const color = OS_COLORS[host.os] || '#555'
    const label = host.name.split('.')[0]
    return L.divIcon({
      className: '',
      html: `
        <div class="host-pin" style="--os-color: ${color}">
          <span class="host-pin-label">${label}</span>
        </div>`,
      iconSize: [null, null],
      iconAnchor: [0, 12],
    })
  }

  $effect(() => {
    if (tenant) loadMap()
  })
</script>

<div class="page">
  <div class="map-header">
    <span class="title">MAP</span>
    <span class="zoom-hint">
      {#if zoomLevel >= ZOOM_THRESHOLD}
        hosts — click to inspect
      {:else}
        zoom in to see individual hosts
      {/if}
    </span>
    {#if loading}
      <div style="color: var(--text-muted); margin-left: auto;">Loading...</div>
    {/if}
  </div>

  {#if error}
    <div class="error-msg">Error: {error}</div>
  {/if}

  <div class="map-container">
    <div id="leaflet-map"></div>

    {#if locationsWithoutCoords.length > 0}
      <div class="locations-list">
        <h3>Locations without coordinates</h3>
        {#each locationsWithoutCoords as loc}
          <div class="location-item">
            <div class="location-name">{loc.display_name}</div>
            {#if loc.address}
              <div class="location-address">{loc.address}</div>
            {/if}
            <div class="location-count">{loc.host_count} host{loc.host_count !== 1 ? 's' : ''}</div>
            {#if loc.hosts && loc.hosts.length > 0}
              <div class="location-hosts">
                {#each loc.hosts as host}
                  <div class="host-item">{host.name} ({host.os})</div>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>

  {#if selectedHost}
    <div class="host-sheet" style="--os-color: {OS_COLORS[selectedHost.os] || '#555'}">
      <div class="sheet-header">
        <span class="sheet-hostname">{selectedHost.name}</span>
        <span class="os-badge">{selectedHost.os}</span>
        <button class="sheet-close" onclick={() => (selectedHost = null)} title="Close">✕</button>
      </div>
      <div class="sheet-body">
        <div class="sheet-row">
          <span class="sheet-key">Location</span>
          <span>{selectedHost.display_name}</span>
        </div>
        {#if (selectedHost.groups || []).length}
          <div class="sheet-row">
            <span class="sheet-key">Groups</span>
            <div class="tag-list">
              {#each selectedHost.groups || [] as g}
                <span class="tag">{g}</span>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg);
  }

  .map-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px 28px;
    border-bottom: 1px solid var(--border);
    background: linear-gradient(90deg, var(--bg-2) 0%, rgba(15, 22, 41, 0.5) 100%);
  }

  .title {
    font-size: clamp(10px, 1.6vw, 11px);
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .zoom-hint {
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--mono);
    letter-spacing: 0.04em;
  }

  .error-msg {
    padding: 16px;
    background: rgba(248, 81, 73, 0.1);
    color: var(--error);
    border-bottom: 1px solid var(--border);
  }

  .map-container {
    flex: 1;
    display: flex;
    gap: 20px;
    padding: 24px 28px;
    overflow: hidden;
    position: relative;
    z-index: 1;
  }

  #leaflet-map {
    flex: 1;
    border-radius: 4px;
    border: 1px solid var(--border);
    touch-action: manipulation;
  }

  :global(.leaflet-container) {
    background: var(--bg-2);
    border-radius: 4px;
  }

  :global(.leaflet-pane) {
    pointer-events: auto;
  }

  :global(.leaflet-control-container) {
    pointer-events: auto;
  }

  :global(.leaflet-popup-content-wrapper) {
    background: var(--bg-2);
    color: var(--text);
    border-color: var(--border);
  }

  :global(.leaflet-popup-tip) {
    background: var(--bg-2);
  }

  :global(.leaflet-control-zoom a) {
    width: 44px !important;
    height: 44px !important;
    line-height: 44px !important;
    font-size: 18px !important;
  }

  /* Location pin — pill badge */
  :global(.loc-pin) {
    display: flex;
    align-items: center;
    gap: 5px;
    background: var(--bg-2);
    border: 1.5px solid var(--ring, var(--accent));
    border-radius: 20px;
    padding: 4px 10px 4px 8px;
    white-space: nowrap;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
    transition: transform 120ms, box-shadow 120ms;
    font-family: var(--ui);
  }

  :global(.loc-pin:hover) {
    transform: scale(1.06);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
  }

  :global(.loc-pin-name) {
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    color: var(--text);
    text-transform: lowercase;
    letter-spacing: 0.04em;
  }

  :global(.loc-pin-count) {
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    color: var(--accent);
    background: rgba(0, 212, 170, 0.1);
    border-radius: 10px;
    padding: 1px 6px;
  }

  /* Host pin — compact chip */
  :global(.host-pin) {
    display: flex;
    align-items: center;
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--os-color);
    border-radius: 3px;
    padding: 3px 8px;
    white-space: nowrap;
    cursor: pointer;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
    transition: transform 100ms, border-color 100ms;
  }

  :global(.host-pin:hover) {
    transform: translateY(-2px);
    border-color: var(--os-color);
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.5);
  }

  :global(.host-pin-label) {
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    color: var(--text);
  }

  /* Bottom sheet — host detail panel */
  .host-sheet {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    max-height: 55vh;
    background: var(--bg-2);
    border-top: 1px solid var(--border);
    border-left: 4px solid var(--os-color);
    z-index: 1000;
    overflow-y: auto;
    animation: sheetIn 250ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  @keyframes sheetIn {
    from {
      transform: translateY(100%);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  .sheet-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 24px;
    border-bottom: 1px solid var(--border-muted);
    position: sticky;
    top: 0;
    background: var(--bg-2);
    z-index: 1;
  }

  .sheet-hostname {
    font-family: var(--mono);
    font-weight: 700;
    font-size: 14px;
    color: var(--text);
    flex: 1;
  }

  .os-badge {
    padding: 2px 6px;
    border-radius: 2px;
    font-size: 10px;
    font-weight: 700;
    background: rgba(255, 255, 255, 0.06);
    color: var(--os-color);
  }

  .sheet-close {
    min-height: 44px;
    min-width: 44px;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 16px;
    transition: color 100ms;
  }

  .sheet-close:hover {
    color: var(--text);
  }

  .sheet-body {
    padding: 14px 24px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .sheet-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
  }

  .sheet-key {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    width: 80px;
    flex-shrink: 0;
  }

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .tag {
    font-family: var(--mono);
    font-size: 10px;
    padding: 2px 6px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 2px;
    color: var(--text-muted);
  }

  @media (max-width: 768px) {
    .map-container {
      flex-direction: column;
      padding: 12px 16px;
      gap: 12px;
    }

    .locations-list {
      width: 100%;
      max-height: 200px;
    }

    .map-header {
      padding: 14px 16px;
    }
  }

  @media (max-width: 640px) {
    .map-container {
      flex-direction: column;
      padding: 12px 16px;
      gap: 12px;
    }

    .locations-list {
      width: 100%;
      max-height: 40vh;
      overflow-y: auto;
    }

    #leaflet-map {
      min-height: 300px;
    }

    .zoom-hint {
      display: none;
    }

    .host-sheet {
      max-height: 50vh;
    }
  }

  .locations-list {
    width: 280px;
    padding: 12px;
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .locations-list h3 {
    margin: 0;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .location-item {
    padding: 12px 14px;
    background: var(--bg-3);
    border: 1px solid var(--border-muted);
    border-radius: 4px;
    font-size: clamp(12px, 2.5vw, 13px);
    min-height: 44px;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }

  .location-name {
    font-weight: 700;
    color: var(--text);
    margin-bottom: 4px;
    font-size: clamp(13px, 2.8vw, 14px);
    font-family: var(--ui);
  }

  .location-address {
    font-size: clamp(11px, 2.2vw, 12px);
    color: var(--text-muted);
    margin-bottom: 4px;
    line-height: 1.3;
    font-family: var(--ui);
  }

  .location-count {
    font-size: clamp(11px, 2.2vw, 12px);
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 4px;
  }

  .location-hosts {
    font-size: clamp(10px, 2vw, 11px);
    color: var(--text-dim);
    border-top: 1px solid var(--border-muted);
    padding-top: 4px;
    margin-top: 4px;
    font-family: var(--ui);
  }

  .host-item {
    padding: 2px 0;
    font-family: var(--mono);
    font-size: clamp(10px, 2vw, 11px);
  }
</style>
