<script>
  import Test from './Test.svelte'
  import TopologyPage from './pages/TopologyPage.svelte'

  let currentPage = 'test'
</script>

<div class="app-wrapper">
  <nav class="top-nav">
    <div class="nav-brand">Flamelet</div>
    <div class="nav-links">
      <button class:active={currentPage === 'test'} on:click={() => currentPage = 'test'}>Dashboard</button>
      <button class:active={currentPage === 'topology'} on:click={() => currentPage = 'topology'}>Topology</button>
    </div>
  </nav>

  <div class="page-container">
    {#if currentPage === 'test'}
      <Test />
    {:else if currentPage === 'topology'}
      <TopologyPage />
    {/if}
  </div>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    background: #0d1117;
    color: #e6edf3;
    font-family: system-ui, -apple-system, sans-serif;
  }

  .app-wrapper {
    display: flex;
    flex-direction: column;
    height: 100vh;
  }

  .top-nav {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 20px;
    height: 50px;
    background: #0d1117;
    border-bottom: 1px solid #30363d;
  }

  .nav-brand {
    font-weight: 700;
    font-size: 14px;
    letter-spacing: -0.3px;
  }

  .nav-links {
    display: flex;
    gap: 8px;
    margin-left: auto;
  }

  .nav-links button {
    padding: 6px 12px;
    background: transparent;
    border: 1px solid transparent;
    color: #7d8590;
    font-size: 13px;
    cursor: pointer;
    border-radius: 4px;
    transition: all 150ms;
  }

  .nav-links button:hover {
    color: #e6edf3;
    border-color: #30363d;
  }

  .nav-links button.active {
    color: #00d4aa;
    border-color: #00d4aa;
    background: rgba(0, 212, 170, 0.08);
  }

  .page-container {
    flex: 1;
    overflow: hidden;
  }
</style>
