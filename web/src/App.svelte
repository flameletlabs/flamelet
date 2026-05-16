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
      <div class="tenant-wrap">
        <select class="tenant-select" bind:value={selectedTenant}>
          {#each tenants as tenant}
            <option value={tenant.name}>{tenant.name}</option>
          {/each}
        </select>
        <span class="select-arrow" aria-hidden="true">⌄</span>
      </div>
    </div>

    <div class="header-right">
      <button class="theme-toggle" onclick={toggleDarkMode} title="Toggle theme">
        {isDarkMode ? '☀' : '◑'}
      </button>
    </div>
  </header>

  <div class="tab-nav-wrapper">
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
  </div>

  <div class="page-container">
    {#if currentPage === 'tenants'}
      <Tenants tenant={selectedTenant} onTenantChange={(name) => selectedTenant = name} />
    {:else if currentPage === 'operations'}
      <Operations tenant={selectedTenant} />
    {:else if currentPage === 'services'}
      <ServicesPage tenant={selectedTenant} />
    {:else if currentPage === 'execute'}
      <RunPage tenant={selectedTenant} />
    {:else if currentPage === 'map'}
      <MapPage tenant={selectedTenant} />
    {:else if currentPage === 'topology'}
      <TopologyPage tenant={selectedTenant} />
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

  /* dvh gives true mobile viewport (excludes address bar); vh fallback for older browsers */
  .app-wrapper {
    display: flex;
    flex-direction: column;
    height: 100vh;
    height: 100dvh;
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
    gap: 12px;
    flex-shrink: 0;
    min-width: 0;
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

  /* Takes all remaining space, never squeezes below a reasonable minimum */
  .header-center {
    flex: 1;
    min-width: 0;
    max-width: 280px;
  }

  /* Wrapper gives us a positioning context for the custom arrow */
  .tenant-wrap {
    position: relative;
    width: 100%;
  }

  .tenant-select {
    width: 100%;
    padding: 7px 32px 7px 12px;
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
    /* Prevent text overflow on long tenant names */
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
  }

  .tenant-select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.12);
  }

  /* Custom dropdown arrow replacing the native one removed by appearance:none */
  .select-arrow {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-52%);
    color: var(--text-dim);
    font-size: 16px;
    line-height: 1;
    pointer-events: none;
    user-select: none;
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
    width: 44px;
    height: 44px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 44px;
    min-width: 44px;
  }

  .theme-toggle:hover {
    border-color: var(--text-muted);
    color: var(--text);
    background: var(--bg-3);
  }

  /* ── Tab Nav ────────────────────────────────────────────── */

  /* Wrapper enables the scroll-fade indicators via pseudo-elements */
  .tab-nav-wrapper {
    position: relative;
    background: var(--bg-2);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  /* Right fade: shows when content overflows right */
  .tab-nav-wrapper::after {
    content: '';
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 32px;
    background: linear-gradient(to right, transparent, var(--bg-2));
    pointer-events: none;
    z-index: 1;
  }

  .tab-nav {
    display: flex;
    padding: 0 24px;
    overflow-x: auto;
    scrollbar-width: none;
    /* Smooth momentum scrolling on iOS */
    -webkit-overflow-scrolling: touch;
    scroll-snap-type: x proximity;
  }

  .tab-nav::-webkit-scrollbar { display: none; }

  .tab-nav button {
    padding: 0 16px;
    height: 48px;
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
    min-height: 48px;
    min-width: 44px;
    scroll-snap-align: start;
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
    min-height: 0;
  }

  /* ── Responsive: tablet ──────────────────────────────────── */
  @media (max-width: 768px) {
    .top-header {
      padding: 0 16px;
      height: 52px;
      gap: 10px;
    }

    .tab-nav {
      padding: 0 12px;
    }

    .tab-nav button {
      padding: 0 12px;
      font-size: 12px;
    }

    /* Allow Execute page to scroll the whole panel vertically on mobile */
    .page-container {
      overflow-y: auto;
    }
  }

  /* ── Responsive: mobile ──────────────────────────────────── */
  @media (max-width: 480px) {
    .top-header {
      padding: 0 12px;
      height: 48px;
      gap: 8px;
    }

    /* Hide text, keep only the ▲ glyph to reclaim ~60px for tenant select */
    .brand {
      display: none;
    }

    /* Tenant select can now stretch more since brand text is hidden */
    .header-center {
      max-width: none;
    }

    .tenant-select {
      font-size: 12px;
    }

    .tab-nav {
      padding: 0 8px;
    }

    .tab-nav button {
      padding: 0 12px;
      font-size: 11px;
      height: 44px;
      min-height: 44px;
    }
  }

  /* ── Responsive: very small phones ──────────────────────── */
  @media (max-width: 360px) {
    .top-header {
      padding: 0 8px;
      gap: 6px;
    }

    .tab-nav button {
      padding: 0 8px;
      font-size: 11px;
    }
  }
</style>
