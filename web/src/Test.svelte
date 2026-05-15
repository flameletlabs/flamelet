<script>
  import { onMount } from 'svelte'

  let tenants = []
  let loading = true

  onMount(async () => {
    try {
      const res = await fetch('/api/tenants')
      tenants = await res.json()
    } catch (e) {
      console.error('Failed to load tenants:', e)
    }
    loading = false
  })
</script>

<div class="dashboard">
  <h1>Dashboard</h1>
  <p>Welcome to Flamelet infrastructure management</p>

  {#if loading}
    <p>Loading...</p>
  {:else if tenants.length > 0}
    <div class="tenants">
      <h2>Tenants</h2>
      {#each tenants as tenant}
        <div class="tenant-card">
          <h3>{tenant.name}</h3>
          <p>{tenant.host_count} hosts</p>
        </div>
      {/each}
    </div>
  {:else}
    <p>No tenants found</p>
  {/if}
</div>

<style>
  .dashboard {
    padding: 20px;
    color: var(--text);
  }

  h1 {
    color: var(--accent);
    margin: 0 0 10px 0;
    font-size: 28px;
  }

  h2 {
    color: var(--accent);
    margin: 20px 0 10px 0;
    font-size: 20px;
  }

  h3 {
    color: var(--accent);
    margin: 0;
  }

  p {
    color: var(--text-muted);
    margin: 0 0 10px 0;
  }

  .tenants {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 16px;
    margin-top: 20px;
  }

  .tenant-card {
    background: var(--bg-2);
    border: 1px solid var(--border);
    padding: 16px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 150ms;
  }

  .tenant-card:hover {
    border-color: var(--accent);
    background: var(--bg-3);
  }
</style>
