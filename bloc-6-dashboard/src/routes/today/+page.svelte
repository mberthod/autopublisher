<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { Post, Persona, PersonaMap } from '$lib/types';
  import PostCard from '$lib/components/PostCard.svelte';

  let posts: Post[] = [];
  let personaMap: PersonaMap = {};
  let loading = true;
  let error = '';

  const today = new Date().toISOString().split('T')[0];
  const todayDisplay = new Date().toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });

  onMount(async () => {
    try {
      const [fetchedPosts, personas] = await Promise.all([
        api.posts.list({ scheduled_for_date: today }),
        api.personas.list(),
      ]);
      personaMap = Object.fromEntries(personas.map(p => [p.id, p]));
      posts = fetchedPosts.filter(p => p.status !== 'published');
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });

  function handleUpdate(updated: Post) {
    posts = posts.map(p => p.id === updated.id ? updated : p);
  }
</script>

<svelte:head><title>Today — SaaS RSE</title></svelte:head>

<main class="page">
  <div class="page-header">
    <h1>Today</h1>
    <p class="subtitle">{todayDisplay} · {posts.length} post{posts.length !== 1 ? 's' : ''} à traiter</p>
  </div>

  {#if loading}
    <div class="loading">Chargement…</div>
  {:else if error}
    <div class="error-banner">{error}</div>
  {:else if posts.length === 0}
    <div class="empty-state">
      <div class="icon">✅</div>
      <p>Aucun post à traiter aujourd'hui.</p>
    </div>
  {:else}
    <div class="post-grid">
      {#each posts as post (post.id)}
        <PostCard {post} persona={personaMap[post.persona_id]} onUpdate={handleUpdate} />
      {/each}
    </div>
  {/if}
</main>

<style>
  .post-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 16px;
  }
</style>
