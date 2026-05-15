<script>
  import { onMount } from 'svelte'
  import { getServices, getServiceDetail, getTenantHosts, getHostServices } from '../lib/api.js'

  export let tenant = null

  let viewMode = 'services'
  let services = []
  let hosts = []
  let search = ''
  let loading = true
  let error = null
  let expandedService = null
  let serviceDetails = {}

  async function loadServices() {
    if (!tenant) return
    loading = true
    error = null

    try {
      services = await getServices(tenant)
      services.sort((a, b) => b.host_count - a.host_count)
    } catch (e) {
      error = e.message
      console.error('Failed to load services:', e)
    } finally {
      loading = false
    }
  }

  async function loadHostsServices() {
    if (!tenant) return
    loading = true
    error = null

    try {
      hosts = await getTenantHosts(tenant)

      const hostDataPromises = hosts.map(async (host) => {
        const hostServices = await getHostServices(tenant, host.name)
        return { host, services: hostServices }
      })

      const hostData = await Promise.all(hostDataPromises)
      hosts = hostData.map(({ host, services: svc }) => ({ ...host, services: svc }))
    } catch (e) {
      error = e.message
      console.error('Failed to load host services:', e)
    } finally {
      loading = false
    }
  }

  async function toggleServiceExpand(serviceName) {
    if (expandedService === serviceName) {
      expandedService = null
    } else {
      expandedService = serviceName
      if (!serviceDetails[serviceName]) {
        try {
          serviceDetails[serviceName] = await getServiceDetail(tenant, serviceName)
        } catch (e) {
          console.error('Failed to load service detail:', e)
        }
      }
    }
  }

  let filteredServices = []
  let filteredHosts = []

  $: {
    const searchLower = search.toLowerCase()
    if (viewMode === 'services') {
      filteredServices = services.filter(s => {
        const name = s.name.replace(/_/g, ' ').toLowerCase()
        const attr = (s.config_attr || '').toLowerCase()
        return !searchLower || name.includes(searchLower) || attr.includes(searchLower)
      })
    } else {
      filteredHosts = hosts.filter(h => {
        return !searchLower || h.name.toLowerCase().includes(searchLower)
      })
    }
  }

  $: if (tenant && viewMode === 'services') loadServices()
  $: if (tenant && viewMode === 'hosts') loadHostsServices()
</script>

<div class="page">
  <div class="toolbar">
    <div>
      <span class="title">SERVICES</span>
      <span class="count mono">{viewMode === 'services' ? services.length : hosts.length} {viewMode === 'services' ? 'services' : 'hosts'}</span>
    </div>

    <select bind:value={viewMode} class="view-select">
      <option value="services">View: Services</option>
      <option value="hosts">View: Hosts</option>
    </select>

    <input type="search" placeholder="search…" bind:value={search} class="search-input" />
  </div>

  {#if error}
    <div class="error-msg">Error: {error}</div>
  {/if}

  <div class="content">
    {#if loading}
      <div class="loading">Loading...</div>
    {:else if viewMode === 'services'}
      {#if filteredServices.length === 0}
        <div class="empty-msg">
          {search ? 'No services match your search' : 'No services configured'}
        </div>
      {:else}
        <div class="services-list">
          {#each filteredServices as service}
            <div class="service-item" class:expanded={expandedService === service.name}>
              <div class="service-header" role="button" tabindex="0" on:click={() => toggleServiceExpand(service.name)} on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && toggleServiceExpand(service.name)}>
                <span class="chevron">›</span>
                <div class="service-name">{service.name.replace(/_/g, ' ')}</div>
                <div class="service-badge">{service.config_attr}</div>
                <div class="service-count">{service.host_count} host{service.host_count !== 1 ? 's' : ''}</div>
              </div>

              {#if expandedService === service.name && serviceDetails[service.name]}
                <div class="service-detail">
                  {#each serviceDetails[service.name].hosts || [] as host}
                    <div class="detail-row">
                      <div class="detail-hostname">{host.hostname}</div>
                      <div>
                        {#if host.check_count}
                          <div style="margin-bottom: 6px; font-weight: 600;">{host.check_count} checks</div>
                        {/if}
                        <div class="service-keys">
                          {#each host.config_keys || [] as key}
                            <span class="service-key">{key}</span>
                          {/each}
                        </div>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}

              {#if service.hosts && service.hosts.length > 0}
                <div class="service-hosts">
                  {#each service.hosts.slice(0, 5) as hostName}
                    <span class="host-tag">{hostName}</span>
                  {/each}
                  {#if service.hosts.length > 5}
                    <span class="host-tag">+{service.hosts.length - 5} more</span>
                  {/if}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    {:else}
      {#if filteredHosts.length === 0}
        <div class="empty-msg">
          {search ? 'No hosts match your search' : 'No hosts in this tenant'}
        </div>
      {:else}
        <div class="hosts-list">
          {#each filteredHosts as host}
            <div class="host-item">
              <div class="host-header">
                <div class="host-name">{host.name}</div>
                <div class="service-count">{host.services.length} service{host.services.length !== 1 ? 's' : ''}</div>
              </div>
              {#if host.services.length > 0}
                <div class="service-hosts">
                  {#each host.services as service}
                    <span class="host-tag">{service.name.replace(/_/g, ' ')}</span>
                  {/each}
                </div>
              {:else}
                <div style="color: var(--text-dim); font-size: 12px; margin-top: 4px;">No services configured</div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
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

  .toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px 28px;
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

  .count {
    font-size: clamp(11px, 2vw, 12px);
    color: var(--text-muted);
    margin-left: 8px;
    font-family: var(--ui);
  }

  .view-select {
    padding: 5px 10px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--ui);
    font-size: 12px;
    border-radius: 2px;
    cursor: pointer;
    margin-left: auto;
  }

  .view-select:focus {
    outline: none;
    border-color: var(--accent);
  }

  .search-input {
    padding: 5px 10px;
    background: var(--bg-3);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--ui);
    font-size: 12px;
    border-radius: 2px;
    width: 200px;
    outline: none;
  }

  .search-input:focus {
    border-color: var(--accent);
  }

  .error-msg {
    padding: 12px 16px;
    background: rgba(248, 81, 73, 0.1);
    color: var(--error);
    font-size: 12px;
    border-bottom: 1px solid var(--border);
  }

  .content {
    flex: 1;
    overflow-y: auto;
  }

  .loading,
  .empty-msg {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-muted);
  }

  .services-list,
  .hosts-list {
    padding: 24px 28px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .service-item,
  .host-item {
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
  }

  .service-header,
  .host-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 18px;
    cursor: pointer;
    user-select: none;
  }

  .service-item:not(.expanded) .service-header:hover,
  .host-item:hover {
    background: var(--bg-3);
  }

  .chevron {
    display: inline-block;
    transform: rotate(90deg);
    transition: transform 150ms;
    color: var(--text-muted);
    font-size: 14px;
  }

  .service-item.expanded .chevron {
    transform: rotate(180deg);
  }

  .service-name,
  .host-name {
    font-weight: 700;
    color: var(--text);
    flex: 1;
    font-size: clamp(13px, 3vw, 15px);
    text-transform: capitalize;
    font-family: var(--ui);
  }

  .service-badge {
    background: var(--bg-3);
    color: var(--text-muted);
    padding: 2px 8px;
    border-radius: 2px;
    font-size: 10px;
    font-family: var(--mono);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .service-count {
    font-size: clamp(11px, 2vw, 12px);
    color: var(--text-muted);
  }

  .service-hosts {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    padding: 0 16px 12px;
  }

  .host-tag {
    background: var(--bg-3);
    color: var(--text-muted);
    padding: 3px 8px;
    border-radius: 3px;
    font-size: clamp(11px, 2vw, 12px);
    font-family: var(--ui);
  }

  .service-detail {
    padding: 12px 16px 0;
    border-top: 1px solid var(--border-muted);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .detail-row {
    padding: 8px;
    background: var(--bg-3);
    border-radius: 2px;
    border-left: 2px solid var(--accent);
  }

  .detail-hostname {
    font-family: var(--mono);
    font-weight: 600;
    color: var(--text);
    margin-bottom: 4px;
    font-size: clamp(12px, 2.2vw, 13px);
  }

  .service-keys {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }

  .service-key {
    background: var(--bg);
    color: var(--text-dim);
    padding: 2px 6px;
    border-radius: 2px;
    font-size: 10px;
    font-family: var(--mono);
  }

  @media (max-width: 900px) {
    .header {
      padding: clamp(8px, 1.2vw, 12px) clamp(12px, 1.5vw, 16px);
    }

    .title {
      font-size: clamp(10px, 1.4vw, 12px);
    }

    .toggle-group {
      gap: clamp(6px, 1vw, 8px);
    }

    .toggle-btn {
      font-size: clamp(9px, 1.2vw, 10px);
      padding: clamp(4px, 0.8vw, 6px) clamp(8px, 1.2vw, 10px);
    }

    .service-item {
      margin: clamp(4px, 0.8vw, 6px);
      padding: clamp(8px, 1.2vw, 10px);
    }

    .service-name {
      font-size: clamp(12px, 1.6vw, 13px);
    }
  }

  @media (max-width: 768px) {
    .layout {
      grid-template-columns: 1fr;
    }

    aside {
      max-height: 200px;
      border-right: none;
      border-bottom: 1px solid var(--border);
    }

    .content {
      min-height: 0;
    }

    .header {
      padding: clamp(8px, 1.2vw, 10px);
    }

    .title {
      font-size: clamp(10px, 1.3vw, 11px);
    }

    .toggle-btn {
      font-size: clamp(8px, 1vw, 9px);
      padding: clamp(3px, 0.6vw, 4px) clamp(6px, 1vw, 8px);
    }

    .filter-input {
      padding: clamp(4px, 0.8vw, 5px);
      font-size: clamp(10px, 1.2vw, 11px);
    }

    .search-label {
      font-size: clamp(8px, 1vw, 9px);
    }
  }

  @media (max-width: 640px) {
    aside {
      max-height: 150px;
    }

    .header {
      flex-direction: column;
      gap: clamp(6px, 1vw, 8px);
      padding: clamp(6px, 1vw, 8px);
    }

    .toggle-group {
      width: 100%;
    }

    .toggle-btn {
      flex: 1;
      font-size: clamp(8px, 1vw, 9px);
    }

    .service-name {
      font-size: clamp(11px, 1.4vw, 12px);
    }

    .detail-hostname {
      font-size: clamp(10px, 1.2vw, 11px);
    }

    .service-key {
      font-size: 9px;
    }
  }

  @media (max-width: 480px) {
    aside {
      max-height: 120px;
    }

    .header {
      padding: 6px 8px;
    }

    .service-item {
      margin: 3px;
      padding: 6px 8px;
    }

    .service-name {
      font-size: 11px;
    }

    .toggle-btn {
      font-size: 8px;
      padding: 3px 6px;
    }

    .filter-input {
      font-size: 10px;
    }
  }
</style>
