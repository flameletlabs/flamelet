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
    font-family: var(--sans);
  }

  .app-wrapper {
    display: flex;
    flex-direction: column;
    height: 100vh;
  }

  .top-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    background: var(--bg-2);
    border-bottom: 1px solid var(--border);
    gap: 20px;
    position: relative;
    z-index: 100;
  }

  .header-left {
    flex: 0 0 auto;
  }

  .brand {
    margin: 0;
    font-size: clamp(14px, 2vw, 16px);
    font-weight: 700;
    color: var(--text);
    font-family: 'Dosis', sans-serif;
    letter-spacing: -0.3px;
    text-transform: uppercase;
    font-size: clamp(13px, 1.8vw, 15px);
  }

  .header-center {
    flex: 0 0 auto;
  }

  .tenant-select {
    padding: clamp(5px, 1.2vw, 8px) clamp(10px, 1.5vw, 14px);
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-family: var(--ui);
    font-size: clamp(11px, 1.6vw, 12px);
    font-weight: 500;
    cursor: pointer;
    line-height: 1.5;
    -webkit-appearance: none;
    appearance: none;
  }

  .tenant-select:hover {
    border-color: var(--accent);
  }

  .header-right {
    flex: 0 0 auto;
  }

  .theme-toggle {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    transition: background 150ms;
  }

  .theme-toggle:hover {
    background: var(--bg-3);
  }

  .tab-nav {
    display: flex;
    gap: 0;
    padding: 0 20px;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    align-items: center;
    position: relative;
    z-index: 99;
  }

  .tab-nav button {
    padding: clamp(10px, 1.5vw, 12px) clamp(12px, 2vw, 16px);
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: clamp(10px, 1.5vw, 12px);
    font-family: var(--ui);
    font-weight: 600;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    line-height: 1.4;
    transition: color 150ms, border-color 150ms;
    border-bottom: 3px solid transparent;
    margin-bottom: -1px;
  }

  .tab-nav button:hover {
    color: var(--text);
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
    font-size: 14px;
  }

  @media (max-width: 900px) {
    .top-header {
      padding: clamp(6px, 1vw, 10px) clamp(10px, 1.5vw, 16px);
      gap: clamp(8px, 1.5vw, 16px);
    }

    .tab-nav {
      padding: 0 clamp(8px, 1.5vw, 16px);
    }

    .tab-nav button {
      padding: clamp(8px, 1.2vw, 10px) clamp(10px, 1.5vw, 14px);
    }
  }

  @media (max-width: 768px) {
    .top-header {
      padding: clamp(6px, 1.2vw, 8px) clamp(10px, 1.5vw, 12px);
      gap: clamp(6px, 1.2vw, 10px);
      flex-wrap: wrap;
    }

    .tenant-select {
      padding: clamp(4px, 0.8vw, 6px) clamp(8px, 1.2vw, 10px);
      font-size: clamp(11px, 1.6vw, 12px);
    }

    .theme-toggle {
      font-size: clamp(14px, 2vw, 16px);
      padding: clamp(2px, 0.5vw, 4px);
    }
  }

  @media (max-width: 640px) {
    .top-header {
      gap: clamp(6px, 1.2vw, 8px);
      padding: clamp(6px, 1vw, 8px) clamp(8px, 1.2vw, 10px);
    }

    .header-left {
      flex: 1;
    }

    .header-center {
      order: 3;
      flex: 1 100%;
    }

    .brand {
      font-size: clamp(11px, 1.8vw, 12px);
    }

    .tenant-select {
      width: 100%;
      padding: clamp(4px, 0.8vw, 5px) clamp(6px, 1vw, 8px);
      font-size: clamp(10px, 1.4vw, 11px);
    }

    .tab-nav {
      padding: 0 clamp(6px, 1vw, 8px);
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }

    .tab-nav button {
      padding: clamp(8px, 1vw, 10px) clamp(8px, 1.2vw, 12px);
      font-size: clamp(10px, 1.4vw, 11px);
      flex-shrink: 0;
    }
  }

  @media (max-width: 480px) {
    .top-header {
      padding: clamp(6px, 0.8vw, 7px) clamp(6px, 1vw, 8px);
    }

    .brand {
      font-size: clamp(10px, 1.5vw, 11px);
    }

    .tenant-select {
      font-size: clamp(9px, 1.2vw, 10px);
      padding: clamp(3px, 0.6vw, 4px) clamp(5px, 0.8vw, 6px);
    }

    .tab-nav button {
      padding: clamp(6px, 0.8vw, 8px) clamp(6px, 1vw, 10px);
      font-size: clamp(9px, 1.2vw, 10px);
    }
  }
</style>
