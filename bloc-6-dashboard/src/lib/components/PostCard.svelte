<script lang="ts">
  import type { Post, Persona } from '$lib/types';
  import { errorLabel } from '$lib/types';
  import { api } from '$lib/api';
  import StatusBadge from './StatusBadge.svelte';
  import PlatformIcon from './PlatformIcon.svelte';

  export let post: Post;
  export let persona: Persona | undefined = undefined;
  export let onUpdate: (updated: Post) => void = () => {};

  const buLabels: Record<string, string> = {
    noisyless: 'Noisyless',
    afluxo: 'Afluxo',
    mbhrep: 'MBHREP',
  };
  const formatLabels: Record<string, string> = {
    text_only: 'Texte',
    image: 'Image',
    carousel: 'Carrousel',
  };

  let loading = false;
  let errorMsg = '';
  let publishHint = false;

  async function action(newStatus: string) {
    loading = true;
    errorMsg = '';
    try {
      const updated = await api.posts.update(post.id, { status: newStatus as Post['status'] });
      onUpdate(updated);
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  // Mode manuel : passe le post en file de publication immédiate (scheduled, daté maintenant).
  // La publication réelle se déclenche depuis le popup de l'extension → « Publier maintenant ».
  async function publishNow() {
    loading = true;
    errorMsg = '';
    try {
      const updated = await api.posts.update(post.id, {
        status: 'scheduled',
        scheduled_for: new Date().toISOString(),
      });
      onUpdate(updated);
      publishHint = true;
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }
</script>

<article class="post-card">
  <header>
    <div class="tags">
      {#if persona}
        <span class="bu-tag bu-{persona.bu}">{buLabels[persona.bu] ?? persona.bu}</span>
      {/if}
      <PlatformIcon platform={post.platform} size={18} />
      <span class="format-tag">{formatLabels[post.format] ?? post.format}</span>
      <StatusBadge status={post.status} />
    </div>
    {#if post.scheduled_for}
      <time class="scheduled-time">{new Date(post.scheduled_for).toLocaleString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</time>
    {/if}
  </header>

  {#if post.text}
    <p class="post-text">{post.text.slice(0, 200)}{post.text.length > 200 ? '…' : ''}</p>
  {:else}
    <p class="post-angle">{post.angle_editorial}</p>
  {/if}

  {#if post.image_url}
    <a href={post.image_url} target="_blank" rel="noopener" class="media-link">Voir l'image →</a>
  {/if}
  {#if post.carousel_urls?.length}
    <span class="media-link">{post.carousel_urls.length} slide(s) de carrousel</span>
  {/if}

  {#if post.status === 'failed'}
    <div class="error-line" title={post.error_message ?? ''}>⚠ {errorLabel(post.error_code)}</div>
  {/if}

  {#if post.published_url}
    <a href={post.published_url} target="_blank" rel="noopener" class="media-link">Voir le post publié →</a>
  {/if}

  {#if errorMsg}
    <div class="error-line">{errorMsg}</div>
  {/if}

  {#if publishHint}
    <div class="publish-hint">
      ✅ En file de publication. Ouvre l'extension et clique <strong>« ▶ Publier maintenant »</strong> pour lancer la publication.
    </div>
  {/if}

  <footer>
    {#if post.status !== 'published'}
      <button class="btn btn-publish btn-sm" on:click={publishNow} disabled={loading} title="Passe le post en file et se publie via l'extension">
        {loading ? '…' : '📤 Publier maintenant'}
      </button>
    {/if}
    {#if post.status === 'draft'}
      <button class="btn btn-secondary btn-sm" on:click={() => action('validated')} disabled={loading}>
        Valider
      </button>
    {:else if post.status === 'failed'}
      <button class="btn btn-secondary btn-sm" on:click={() => action('scheduled')} disabled={loading}>
        Réessayer
      </button>
    {/if}
    <button class="btn btn-danger btn-sm" on:click={() => action('draft')} disabled={loading}>
      Réinitialiser
    </button>
  </footer>
</article>

<style>
  .post-card {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.15s;
  }
  .post-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
  }
  .tags {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .bu-tag {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }
  .bu-noisyless { background: #EDE9FE; color: #5B21B6; }
  .bu-afluxo    { background: #DCFCE7; color: #15803D; }
  .bu-mbhrep    { background: #FEF3C7; color: #92400E; }
  .format-tag {
    font-size: 11px;
    color: #6B7280;
    background: #F3F4F6;
    padding: 2px 7px;
    border-radius: 4px;
  }
  .scheduled-time {
    font-size: 12px;
    color: #6B7280;
    font-weight: 500;
  }

  .post-text {
    font-size: 14px;
    color: #374151;
    margin: 0;
    line-height: 1.55;
  }
  .post-angle {
    font-size: 13px;
    color: #9CA3AF;
    font-style: italic;
    margin: 0;
  }

  .media-link {
    font-size: 12px;
    color: #6C63FF;
    display: inline-block;
  }
  .error-line {
    font-size: 12px;
    color: #B91C1C;
    background: #FEE2E2;
    padding: 6px 10px;
    border-radius: 5px;
  }
  .publish-hint {
    font-size: 12px;
    color: #075985;
    background: #E0F2FE;
    border: 1px solid #7DD3FC;
    padding: 8px 10px;
    border-radius: 6px;
    line-height: 1.4;
  }
  .btn-publish {
    background: #6C63FF;
    color: #fff;
    border-color: #6C63FF;
  }
  .btn-publish:hover:not(:disabled) { background: #5A52E0; }

  footer {
    flex-wrap: wrap;
    display: flex;
    gap: 8px;
    padding-top: 4px;
    border-top: 1px solid #F3F4F6;
  }
</style>
