<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { Post, Persona, PersonaMap } from '$lib/types';
  import PlatformIcon from '$lib/components/PlatformIcon.svelte';

  let posts: Post[] = [];
  let personaMap: PersonaMap = {};
  let loading = true;
  let error = '';

  const BU_LABELS: Record<string, string> = { noisyless: 'Noisyless', afluxo: 'Afluxo', mbhrep: 'MBHREP' };

  onMount(async () => {
    try {
      const [fetchedPosts, personas] = await Promise.all([
        api.posts.list({ status: 'published', limit: '200' }),
        api.personas.list(),
      ]);
      personaMap = Object.fromEntries(personas.map(p => [p.id, p]));
      posts = fetchedPosts.sort((a, b) =>
        new Date(b.published_at ?? b.created_at).getTime() -
        new Date(a.published_at ?? a.created_at).getTime()
      );
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });

  function exportCsv() {
    const rows = [
      ['Date', 'BU', 'Plateforme', 'Format', 'Statut', 'URL'].join(','),
      ...posts.map(p => {
        const bu = personaMap[p.persona_id]?.bu ?? '';
        const date = p.published_at ? new Date(p.published_at).toLocaleDateString('fr-FR') : '';
        return [date, bu, p.platform, p.format, p.status, p.published_url ?? ''].join(',');
      }),
    ].join('\n');
    const blob = new Blob([rows], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'posts-publies.csv';
    a.click();
  }
</script>

<svelte:head><title>Analytics — SaaS RSE</title></svelte:head>

<main class="page">
  <div class="page-header">
    <h1>Analytics</h1>
    <p class="subtitle">{posts.length} post{posts.length !== 1 ? 's' : ''} publié{posts.length !== 1 ? 's' : ''}</p>
  </div>

  <div class="phase-banner">
    <span class="phase-icon">🔜</span>
    <div>
      <strong>Analytics détaillées disponibles en phase B</strong>
      <p>Le scraping des métriques (likes, vues, reach, comments) sera intégré en phase B via les APIs officielles LinkedIn et Instagram.</p>
    </div>
  </div>

  {#if loading}
    <div class="loading">Chargement…</div>
  {:else if error}
    <div class="error-banner">{error}</div>
  {:else if posts.length === 0}
    <div class="empty-state">
      <div class="icon">📊</div>
      <p>Aucun post publié pour l'instant.</p>
    </div>
  {:else}
    <div class="table-header">
      <span class="table-count">{posts.length} post{posts.length !== 1 ? 's' : ''}</span>
      <button class="btn btn-secondary btn-sm" on:click={exportCsv}>Export CSV</button>
    </div>
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>BU</th>
            <th>Plateforme</th>
            <th>Format</th>
            <th>Texte</th>
            <th>URL</th>
          </tr>
        </thead>
        <tbody>
          {#each posts as post (post.id)}
            {@const persona = personaMap[post.persona_id]}
            <tr>
              <td class="date-cell">
                {post.published_at
                  ? new Date(post.published_at).toLocaleDateString('fr-FR')
                  : '—'}
              </td>
              <td>
                {#if persona}
                  <span class="bu-tag bu-{persona.bu}">{BU_LABELS[persona.bu] ?? persona.bu}</span>
                {:else}—{/if}
              </td>
              <td class="platform-cell">
                <PlatformIcon platform={post.platform} size={16} />
                <span>{post.platform}</span>
              </td>
              <td class="format-cell">{post.format}</td>
              <td class="text-cell">{post.text?.slice(0, 80) ?? post.angle_editorial}</td>
              <td>
                {#if post.published_url}
                  <a href={post.published_url} target="_blank" rel="noopener" class="link">Voir →</a>
                {:else}—{/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</main>

<style>
  .phase-banner {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 24px;
  }
  .phase-icon { font-size: 28px; line-height: 1; }
  .phase-banner strong { display: block; color: #1D4ED8; margin-bottom: 4px; }
  .phase-banner p { margin: 0; font-size: 13px; color: #3B82F6; }

  .table-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .table-count { font-size: 13px; color: #6B7280; }

  .table-wrapper {
    overflow-x: auto;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    background: #fff;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  th, td {
    padding: 10px 14px;
    text-align: left;
    border-bottom: 1px solid #F3F4F6;
  }
  th {
    background: #F9FAFB;
    font-weight: 600;
    color: #6B7280;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #FAFAFA; }

  .date-cell { white-space: nowrap; color: #6B7280; font-size: 12px; }
  .platform-cell { display: flex; align-items: center; gap: 6px; text-transform: capitalize; }
  .format-cell { color: #6B7280; font-size: 12px; }
  .text-cell { max-width: 300px; color: #374151; }
  .link { color: #6C63FF; font-size: 12px; }
  .bu-tag {
    padding: 2px 7px; border-radius: 4px;
    font-size: 11px; font-weight: 700; text-transform: uppercase;
  }
  .bu-noisyless { background: #EDE9FE; color: #5B21B6; }
  .bu-afluxo    { background: #DCFCE7; color: #15803D; }
  .bu-mbhrep    { background: #FEF3C7; color: #92400E; }
</style>
