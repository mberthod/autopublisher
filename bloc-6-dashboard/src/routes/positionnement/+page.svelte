<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { Positioning, BU } from '$lib/types';

  let items: Positioning[] = [];
  let loading = true;
  let error = '';
  let savingBu: string | null = null;
  let savedBu: string | null = null;

  const BU_LABELS: Record<BU, string> = { noisyless: 'Noisyless', afluxo: 'Afluxo', mbhrep: 'MBHREP' };

  onMount(async () => {
    try {
      items = await api.positioning.list();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });

  async function save(item: Positioning) {
    savingBu = item.bu;
    savedBu = null;
    error = '';
    try {
      const updated = await api.positioning.update(item.bu, {
        content: item.content ?? '',
        keywords: item.keywords ?? '',
      });
      items = items.map((x) => (x.bu === item.bu ? updated : x));
      savedBu = item.bu;
      setTimeout(() => { if (savedBu === item.bu) savedBu = null; }, 2500);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      savingBu = null;
    }
  }
</script>

<svelte:head><title>Positionnement — SaaS RSE</title></svelte:head>

<main class="page">
  <div class="page-header">
    <div>
      <h1>Positionnement</h1>
      <p class="subtitle">Le positionnement de chaque BU nourrit la génération d'idées et de posts. Édite-le pour améliorer la pertinence.</p>
    </div>
  </div>

  {#if error}<div class="error-banner">{error}</div>{/if}

  {#if loading}
    <div class="loading">Chargement…</div>
  {:else}
    <div class="pos-list">
      {#each items as item (item.bu)}
        <section class="pos-card">
          <header class="pos-head">
            <span class="bu-tag bu-{item.bu}">{BU_LABELS[item.bu] ?? item.bu}</span>
            <div class="head-right">
              {#if savedBu === item.bu}<span class="saved">✅ Enregistré</span>{/if}
              <button class="btn btn-primary btn-sm" on:click={() => save(item)} disabled={savingBu === item.bu}>
                {savingBu === item.bu ? 'Enregistrement…' : 'Enregistrer'}
              </button>
            </div>
          </header>

          <label class="field">
            <span class="field-label">Positionnement <small>(cible, douleur, différenciation, ton — injecté dans tous les prompts)</small></span>
            <textarea bind:value={item.content} rows="16" placeholder="Décris la cible, la douleur concrète, la différenciation, l'anti-positionnement, le ton éditorial…"></textarea>
          </label>

          <label class="field">
            <span class="field-label">Mots-clés / thèmes <small>(utilisés pour la génération d'idées quand tu n'en saisis pas)</small></span>
            <textarea bind:value={item.keywords} rows="3" placeholder="ex: gestion locative Airbnb, nuisances sonores, alternative Minut, RGPD…"></textarea>
          </label>
        </section>
      {/each}
    </div>
  {/if}
</main>

<style>
  .pos-list { display: flex; flex-direction: column; gap: 18px; }
  .pos-card { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; padding: 18px; }
  .pos-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
  .head-right { display: flex; align-items: center; gap: 12px; }
  .saved { color: #15803D; font-size: 13px; font-weight: 600; }
  .bu-tag { padding: 3px 10px; border-radius: 5px; font-size: 12px; font-weight: 700; text-transform: uppercase; }
  .bu-noisyless { background: #EDE9FE; color: #5B21B6; }
  .bu-afluxo { background: #DCFCE7; color: #15803D; }
  .bu-mbhrep { background: #FEF3C7; color: #92400E; }
  .field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
  .field-label { font-size: 12px; font-weight: 700; color: #374151; }
  .field-label small { font-weight: 400; color: #9CA3AF; }
  textarea {
    border: 1px solid #D1D5DB; border-radius: 8px; padding: 10px 12px;
    font-family: inherit; font-size: 13px; line-height: 1.5; resize: vertical;
  }
  textarea:focus { outline: none; border-color: #6C63FF; box-shadow: 0 0 0 3px rgba(108,99,255,0.1); }
</style>
