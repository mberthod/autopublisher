<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { Post, Persona, PersonaMap, SessionStatus } from '$lib/types';
  import PostCard from '$lib/components/PostCard.svelte';

  let posts: Post[] = [];
  let personaMap: PersonaMap = {};
  let sessions: SessionStatus[] = [];
  let loading = true;
  let error = '';

  const PLATFORM_LABELS: Record<string, string> = {
    linkedin: 'LinkedIn', instagram: 'Instagram', meta_suite: 'Meta Business Suite',
  };

  const today = new Date().toISOString().split('T')[0];
  const todayDisplay = new Date().toLocaleDateString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });

  function sessionAge(iso: string): string {
    const mins = Math.round((Date.now() - new Date(iso + 'Z').getTime()) / 60000);
    if (mins < 60) return `il y a ${mins} min`;
    const h = Math.round(mins / 60);
    if (h < 24) return `il y a ${h} h`;
    return `il y a ${Math.round(h / 24)} j`;
  }

  onMount(async () => {
    try {
      const [fetchedPosts, personas, fetchedSessions] = await Promise.all([
        api.posts.list({ scheduled_for_date: today }),
        api.personas.list(),
        api.sessions.list().catch(() => []),
      ]);
      personaMap = Object.fromEntries(personas.map(p => [p.id, p]));
      posts = fetchedPosts.filter(p => p.status !== 'published');
      sessions = fetchedSessions;
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

  <!-- État des sessions : le serveur ne peut publier que si la session est valide -->
  <div class="sessions-bar">
    <span class="sessions-label">Publication serveur</span>
    {#each ['linkedin', 'instagram', 'meta_suite'] as plat}
      {@const s = sessions.find(x => x.platform === plat)}
      <span class="session-chip" class:ok={s?.valid} class:ko={s && !s.valid} class:none={!s}>
        {#if s?.valid}✅ {PLATFORM_LABELS[plat]} · {sessionAge(s.updated_at)}
        {:else if s}⚠️ {PLATFORM_LABELS[plat]} · session expirée
        {:else}⚪ {PLATFORM_LABELS[plat]} · non synchronisée
        {/if}
      </span>
    {/each}
    <span class="sessions-hint">Synchronise depuis l'extension (popup → « Synchroniser mes sessions »).</span>
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
  .sessions-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 18px;
  }
  .sessions-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #6B7280; }
  .session-chip { font-size: 12px; padding: 3px 10px; border-radius: 20px; font-weight: 500; }
  .session-chip.ok { background: #DCFCE7; color: #15803D; }
  .session-chip.ko { background: #FEE2E2; color: #B91C1C; }
  .session-chip.none { background: #F3F4F6; color: #9CA3AF; }
  .sessions-hint { font-size: 11px; color: #9CA3AF; margin-left: auto; }
</style>
