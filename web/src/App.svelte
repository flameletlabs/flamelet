<script>
  import { onMount } from 'svelte'
  import Tenants from './pages/Tenants.svelte'
  import Operations from './pages/Operations.svelte'
  import RunPage from './pages/RunPage.svelte'
  import TopologyPage from './pages/TopologyPage.svelte'
  import MapPage from './pages/MapPage.svelte'
  import ServicesPage from './pages/ServicesPage.svelte'
  import { getTenants } from './lib/api.js'

  let currentPage = $state('tenants')
  let tenants = $state([])
  let selectedTenant = $state(null)
  let isDarkMode = $state(true)

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
      <span class="brand-mark">▲</span>
      <h1 class="brand">Flamelet</h1>
    </div>

    <div class="header-center">
      <select class="tenant-select" bind:value={selectedTenant}>
        {#each tenants as tenant}
          <option value={tenant.name}>{tenant.name}</option>
        {/each}
      </select>
    </div>

    <div class="header-right">
      <button class="theme-toggle" onclick={toggleDarkMode} title="Toggle theme">
        {isDarkMode ? '☀' : '◑'}
      </button>
    </div>
  </header>

  <nav class="tab-nav">
    <button class:active={currentPage === 'tenants'} onclick={() => currentPage = 'tenants'}>
      Hosts
    </button>
    <button class:active={currentPage === 'operations'} onclick={() => currentPage = 'operations'}>
      Operations
    </button>
    <button class:active={currentPage === 'services'} onclick={() => currentPage = 'services'}>
      Services
    </button>
    <button class:active={currentPage === 'topology'} onclick={() => currentPage = 'topology'}>
      Topology
    </button>
    <button class:active={currentPage === 'map'} onclick={() => currentPage = 'map'}>
      Map
    </button>
    <button class:active={currentPage === 'execute'} onclick={() => currentPage = 'execute'}>
      Execute
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

  /* ── Header ────────────────────────────────────────────── */
  .top-header {
    display: flex;
    align-items: center;
    padding: 0 24px;
    height: 56px;
    background: var(--bg-2);
    border-bottom: 1px solid var(--border);
    gap: 16px;
    flex-shrink: 0;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .brand-mark {
    font-size: 14px;
    color: var(--accent);
    line-height: 1;
    display: flex;
    align-items: center;
  }

  .brand {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.3px;
    font-family: var(--ui);
    white-space: nowrap;
  }

  .header-center {
    flex: 1;
    max-width: 280px;
  }

  .tenant-select {
    width: 100%;
    padding: 7px 12px;
    background: var(--bg-3);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-family: var(--ui);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    -webkit-appearance: none;
    appearance: none;
    min-height: 36px;
    outline: none;
  }

  .tenant-select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.12);
  }

  .header-right {
    margin-left: auto;
    flex-shrink: 0;
  }

  .theme-toggle {
    background: none;
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 14px;
    cursor: pointer;
    padding: 0;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: auto;
    min-width: auto;
  }

  .theme-toggle:hover {
    border-color: var(--text-muted);
    color: var(--text);
    background: var(--bg-3);
  }

  /* ── Tab Nav ────────────────────────────────────────────── */
  .tab-nav {
    display: flex;
    padding: 0 24px;
    background: var(--bg-2);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .tab-nav::-webkit-scrollbar { display: none; }

  .tab-nav button {
    padding: 0 16px;
    height: 44px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-dim);
    font-size: 13px;
    font-family: var(--ui);
    font-weight: 500;
    cursor: pointer;
    letter-spacing: 0;
    white-space: nowrap;
    flex-shrink: 0;
    margin-bottom: -1px;
    min-height: auto;
    min-width: auto;
  }

  .tab-nav button:hover {
    color: var(--text-muted);
  }

  .tab-nav button.active {
    color: var(--text);
    border-bottom-color: var(--accent);
    font-weight: 600;
  }

  /* ── Page ───────────────────────────────────────────────── */
  .page-container {
    flex: 1;
    overflow: hidden;
  }

  /* ── Responsive ─────────────────────────────────────────── */
  @media (max-width: 768px) {
    .top-header {
      padding: 0 16px;
      height: 52px;
    }

    .tab-nav {
      padding: 0 8px;
    }

    .tab-nav button {
      padding: 0 12px;
      font-size: 12px;
    }
  }

  @media (max-width: 480px) {
    .top-header {
      padding: 0 12px;
      height: 48px;
      flex-wrap: nowrap;
    }

    .header-center {
      max-width: none;
    }

    .brand {
      font-size: 13px;
    }

    .tab-nav {
      padding: 0 4px;
    }

    .tab-nav button {
      padding: 0 10px;
      font-size: 11px;
    }
  }
</style>
