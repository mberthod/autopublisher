<script lang="ts">
  import { page } from '$app/stores';
</script>

<nav>
  <div class="brand">
    <span class="logo">RSE</span>
    <span class="brand-name">SaaS RSE</span>
  </div>
  <div class="links">
    <a href="/compose" class:active={$page.url.pathname === '/compose'}>Composer</a>
    <a href="/today"     class:active={$page.url.pathname === '/today'}>Today</a>
    <a href="/calendar"  class:active={$page.url.pathname === '/calendar'}>Calendar</a>
    <a href="/analytics" class:active={$page.url.pathname === '/analytics'}>Analytics</a>
    <div class="divider"></div>
    <a href="/personas"  class:active={$page.url.pathname.startsWith('/personas')}>Personas</a>
    <a href="/positionnement" class:active={$page.url.pathname === '/positionnement'}>Positionnement</a>
    <a href="/grillme"   class:active={$page.url.pathname === '/grillme'} class="grillme-link">GrilledMe</a>
  </div>
</nav>

<style>
  nav {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 0 24px;
    height: 56px;
    background: #fff;
    border-bottom: 1px solid #E5E7EB;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-right: 8px;
  }
  .logo {
    background: #6C63FF;
    color: #fff;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 1px;
    padding: 4px 8px;
    border-radius: 5px;
  }
  .brand-name { font-weight: 700; font-size: 15px; }
  .links {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .divider {
    width: 1px;
    height: 20px;
    background: #E5E7EB;
    margin: 0 8px;
  }
  .links a {
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    color: #6B7280;
    transition: background 0.12s, color 0.12s;
  }
  .links a:hover { background: #F3F4F6; color: #111827; }
  .links a.active { background: #EEF2FF; color: #6C63FF; font-weight: 600; }
  .grillme-link { color: #059669; }
  .grillme-link:hover { background: #D1FAE5 !important; color: #065F46 !important; }
  .grillme-link.active { background: #D1FAE5 !important; color: #065F46 !important; }
</style>
