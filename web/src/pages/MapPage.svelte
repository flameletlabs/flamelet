<script>
  import { onMount } from 'svelte'
  import { getLocations } from '../lib/api.js'
  import L from 'leaflet'
  import 'leaflet/dist/leaflet.css'

  export let tenant = null

  let mapInstance = null
  let markers = []
  let locations = []
  let loading = true
  let error = null
  let locationsWithoutCoords = []

  async function loadMap() {
    if (!tenant) return
    loading = true
    error = null

    try {
      locations = await getLocations(tenant)

      if (!mapInstance) {
        initMap()
      }

      markers.forEach(m => mapInstance.removeLayer(m))
      markers = []
      locationsWithoutCoords = []
      let hasCoords = false

      locations.forEach(loc => {
        if (loc.lat !== null && loc.lon !== null) {
          hasCoords = true

          let markerColor = '#3b82f6'
          if (loc.host_count === 0) {
            markerColor = '#9ca3af'
          } else if (loc.host_count >= 10) {
            markerColor = '#10b981'
          }

          const marker = L.circleMarker([loc.lat, loc.lon], {
            radius: 12,
            fillColor: markerColor,
            color: markerColor === '#9ca3af' ? '#6b7280' : '#1e40af',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.85,
          })

          let hostListHtml = ''
          if (loc.hosts && loc.hosts.length > 0) {
            hostListHtml = `
              <div style="margin-top: 8px; max-height: 150px; overflow-y: auto; font-size: 11px;">
                <div style="font-weight: 600; color: var(--text-muted); margin-bottom: 6px;">Hosts:</div>
                ${loc.hosts.map(h => `
                  <div style="padding: 3px 0; color: var(--text-dim);">
                    <code style="background: var(--bg-3); padding: 2px 4px; border-radius: 2px; font-family: var(--mono);">
                      ${h.name}
                    </code>
                    <span style="margin-left: 4px; font-size: 10px; color: var(--text-muted);">${h.os}</span>
                  </div>
                `).join('')}
              </div>
            `
          }

          const popupContent = `
            <div style="font-family: var(--ui); width: 220px;">
              <div style="font-weight: 700; font-size: 13px; margin-bottom: 4px; color: var(--text);">
                ${loc.display_name}
              </div>
              ${loc.address ? `
                <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 6px; line-height: 1.4;">
                  ${loc.address}
                </div>
              ` : ''}
              <div style="font-size: 12px; font-weight: 600; color: var(--accent); padding: 6px 0;">
                ${loc.host_count} host${loc.host_count !== 1 ? 's' : ''}
              </div>
              ${hostListHtml}
            </div>
          `
          marker.bindPopup(popupContent)
          marker.addTo(mapInstance)
          markers.push(marker)
        } else {
          locationsWithoutCoords.push(loc)
        }
      })

      if (hasCoords && markers.length > 0) {
        setTimeout(() => {
          const bounds = L.featureGroup(markers).getBounds()
          mapInstance.fitBounds(bounds, { padding: [50, 50] })
        }, 100)
      }
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
  }

  $: if (tenant) loadMap()
</script>

<div class="page">
  <div class="map-header">
    <h2>Infrastructure Locations</h2>
    {#if loading}
      <div style="color: var(--text-muted);">Loading...</div>
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

  .map-header h2 {
    margin: 0;
    font-size: clamp(16px, 4vw, 18px);
    font-weight: 700;
    color: var(--text);
    font-family: var(--ui);
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

  :global(.marker-cluster) {
    background-color: var(--accent);
    border: 2px solid var(--accent);
  }

  :global(.marker-cluster span) {
    color: var(--bg);
    font-weight: 700;
    font-size: 13px;
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
    transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  .location-item:hover {
    border-color: rgba(0, 212, 170, 0.3);
    background: var(--bg-2);
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
