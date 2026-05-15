<script>
  import { onMount } from 'svelte'
  import Tenants from './pages/Tenants.svelte'
  import Operations from './pages/Operations.svelte'
  import RunPage from './pages/RunPage.svelte'
  import TopologyPage from './pages/TopologyPage.svelte'
  import MapPage from './pages/MapPage.svelte'
  import ServicesPage from './pages/ServicesPage.svelte'
  import { getTenants } from './lib/api.js'

  let currentPage = 'tenants'
  let tenants = []
  let selectedTenant = null
  let isDarkMode = true

  onMount(async () => {
    const saved = localStorage.getItem('flamelet-theme')
    const isDark = saved ? saved === 'dark' : !matchMedia('(prefers-color-scheme: light)').matches
    setTheme(isDark)

    tenants = await getTenants()
    if (tenants.length) selectedTenant = tenants[0].name
  })

  function setTheme(isDark) {
    isDarkMode = isDark
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
    localStorage.setItem('flamelet-theme', isDark ? 'dark' : 'light')
  }

  function toggleDarkMode() {
    setTheme(!isDarkMode)
  }
</script>

<div class="app-wrapper">
  <header class="top-header">
    <div class="header-left">
      <h1 class="brand">Flamelet</h1>
    </div>

    <div class="header-center">
      <select class="tenant-select" bind:value={selectedTenant}>
        {#each tenants as tenant}
          <option value={tenant.name}>
            {tenant.name}
          </option>
        {/each}
      </select>
    </div>

    <div class="header-right">
      <button class="theme-toggle" on:click={toggleDarkMode} title="Toggle dark mode">
        {isDarkMode ? '☀️' : '🌙'}
      </button>
    </div>
  </header>

  <nav class="tab-nav">
    <button class:active={currentPage === 'tenants'} on:click={() => currentPage = 'tenants'}>
      Tenants
    </button>
    <button class:active={currentPage === 'operations'} on:click={() => currentPage = 'operations'}>
      Operations
    </button>
    <button class:active={currentPage === 'map'} on:click={() => currentPage = 'map'}>
      Map
    </button>
    <button class:active={currentPage === 'services'} on:click={() => currentPage = 'services'}>
      Services
    </button>
    <button class:active={currentPage === 'execute'} on:click={() => currentPage = 'execute'}>
      Execute
    </button>
    <button class:active={currentPage === 'topology'} on:click={() => currentPage = 'topology'}>
      Topology
    </button>
  </nav>

  <div class="page-container">
    {#if currentPage === 'tenants'}
      <Tenants />
    {:else if currentPage === 'operations'}
      <Operations tenant={selectedTenant} />
    {:else if currentPage === 'services'}
      <ServicesPage tenant={selectedTenant} />
    {:else if currentPage === 'execute'}
      <RunPage tenant={selectedTenant} />
    {:else if currentPage === 'map'}
      <MapPage tenant={selectedTenant} />
    {:else if currentPage === 'topology'}
      <TopologyPage />
    {/if}
  </div>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--ui);
  }

  .app-wrapper {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .top-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px;
    background: var(--bg-2);
    border-bottom: 1px solid var(--border);
    gap: 12px;
    position: relative;
    z-index: 100;
    flex-wrap: wrap;
  }

  .header-left {
    flex: 0 0 auto;
  }

  .brand {
    margin: 0;
    font-size: clamp(14px, 3vw, 16px);
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.3px;
    text-transform: uppercase;
    font-family: var(--ui);
  }

  .header-center {
    flex: 1;
    min-width: 180px;
  }

  .tenant-select {
    width: 100%;
    padding: 8px 10px;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-family: var(--ui);
    font-size: clamp(12px, 2vw, 13px);
    font-weight: 500;
    cursor: pointer;
    transition: border-color 200ms;
    -webkit-appearance: none;
    appearance: none;
    min-height: 40px;
  }

  .tenant-select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.1);
  }

  .tenant-select:hover {
    border-color: var(--text-muted);
  }

  .header-right {
    flex: 0 0 auto;
  }

  .theme-toggle {
    background: none;
    border: none;
    font-size: 16px;
    cursor: pointer;
    padding: 6px 10px;
    border-radius: 6px;
    transition: background 150ms, transform 150ms;
    display: flex;
    align-items: center;
  }

  .theme-toggle:active {
    transform: scale(0.95);
  }

  .theme-toggle:hover {
    background: var(--bg-3);
  }

  .tab-nav {
    display: flex;
    gap: 0;
    padding: 0 8px;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    align-items: stretch;
    position: relative;
    z-index: 99;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .tab-nav::-webkit-scrollbar {
    display: none;
  }

  .tab-nav button {
    padding: 12px 14px;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: clamp(11px, 1.8vw, 12px);
    font-family: var(--ui);
    font-weight: 600;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    line-height: 1.4;
    transition: color 200ms, background 200ms;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    white-space: nowrap;
    flex-shrink: 0;
    min-height: 44px;
    display: flex;
    align-items: center;
  }

  .tab-nav button:hover {
    color: var(--text);
    background: rgba(0, 212, 170, 0.05);
  }

  .tab-nav button:active {
    background: rgba(0, 212, 170, 0.1);
  }

  .tab-nav button.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }

  .page-container {
    flex: 1;
    overflow: hidden;
  }

  .placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-muted);
    font-size: 13px;
  }

  @media (max-width: 768px) {
    .top-header {
      padding: 12px 12px;
      gap: 10px;
    }

    .brand {
      font-size: 13px;
    }

    .header-center {
      flex: 0 0 100%;
      order: 3;
      min-width: auto;
    }

    .tenant-select {
      padding: 7px 10px;
      font-size: 12px;
    }

    .tab-nav {
      padding: 0 4px;
    }

    .tab-nav button {
      padding: 10px 12px;
      font-size: 11px;
    }
  }

  @media (max-width: 640px) {
    .top-header {
      padding: 10px 10px;
      gap: 8px;
    }

    .brand {
      font-size: 12px;
    }

    .header-center {
      flex: 1;
      order: 2;
      min-width: 0;
    }

    .header-right {
      order: 1;
    }

    .tenant-select {
      padding: 6px 8px;
      font-size: 11px;
    }

    .theme-toggle {
      padding: 5px 8px;
      font-size: 14px;
    }

    .tab-nav {
      padding: 0 2px;
    }

    .tab-nav button {
      padding: 10px 10px;
      font-size: 10px;
    }
  }

  @media (max-width: 480px) {
    .top-header {
      padding: 8px 8px;
      gap: 6px;
    }

    .brand {
      font-size: 11px;
    }

    .tenant-select {
      padding: 5px 6px;
      font-size: 10px;
    }

    .theme-toggle {
      padding: 4px 6px;
      font-size: 13px;
    }

    .tab-nav button {
      padding: 8px 10px;
      font-size: 9px;
    }
  }
</style>
