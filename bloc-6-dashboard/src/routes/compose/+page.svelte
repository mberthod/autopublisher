<script lang="ts">
  import { onMount } from 'svelte';
  import { api, generation } from '$lib/api';
  import type { Persona, Planning } from '$lib/types';
  import { PUBLIC_CAROUSEL_URL } from '$env/static/public';

  // ─── Types ───────────────────────────────────────────────────────────────
  type Platform = 'linkedin' | 'instagram';
  type Format = 'text_only' | 'image' | 'carousel';
  type IdeaStatus = 'pending' | 'generating' | 'done' | 'failed';

  interface Idea {
    id: string;
    angle: string;
    rationale: string;
    platform: Platform;
    selected: boolean;
    status: IdeaStatus;
  }

  interface GenPost {
    id: string;
    post_id: string;
    idea_id: string;
    platform: Platform;
    text: string;
    image_url: string;
    scheduled_for: string;
    status: 'draft' | 'validated' | 'scheduled';
    comment: string;
    saving: boolean;
    regenerating: boolean;
    expanded: boolean;
  }

  // ─── State ───────────────────────────────────────────────────────────────
  let personas: Persona[] = [];
  let plannings: Planning[] = [];
  let loading = true;
  let error = '';

  // Section 1 — Ideas
  let keywords = '';
  let ideas: Idea[] = [];
  let generatingIdeas = false;
  let ideasError = '';
  let newIdeaText = '';
  let addingIdea = false;

  // Section 2 — Config
  let personaId = '';
  let planningId = '';
  let platforms: Platform[] = ['linkedin'];
  let format: Format = 'text_only';
  let intervalDays = 2;
  let startDate = '';
  let bulkGenerating = false;
  let bulkProgress = 0;
  let bulkTotal = 0;
  let bulkError = '';

  // Section 3 — Posts
  let posts: GenPost[] = [];

  const BU_COLORS: Record<string, { bg: string; text: string }> = {
    noisyless: { bg: '#3B2FCC', text: '#E0DCFF' },
    afluxo: { bg: '#0F5233', text: '#CCFCE7' },
    mbhrep: { bg: '#7C3A00', text: '#FEF3C7' },
  };
  const PLAT_COLORS: Record<Platform, string> = { linkedin: '#2563EB', instagram: '#EA580C' };
  const BU_THEMES: Record<string, { bg: string; text: string }> = {
    noisyless: { bg: '#1A0A3D', text: '#D4CAFF' },
    afluxo:    { bg: '#062318', text: '#A7F3D0' },
    mbhrep:    { bg: '#3D1500', text: '#FED7AA' },
  };
  const FORMAT_OPTS: { id: Format; label: string }[] = [
    { id: 'text_only', label: 'Texte' },
    { id: 'image', label: 'Image' },
    { id: 'carousel', label: 'Carrousel' },
  ];

  const ALL_PLATFORMS: Platform[] = ['linkedin', 'instagram'];

  function uid() {
    return Math.random().toString(36).slice(2, 10);
  }

  onMount(async () => {
    try {
      [personas, plannings] = await Promise.all([api.personas.list(), api.plannings.list()]);
      if (personas.length) personaId = personas[0].id;
      if (plannings.length) planningId = plannings[0].id;
      const d = new Date();
      d.setHours(9, 0, 0, 0);
      startDate = d.toISOString().slice(0, 16);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });

  // ─── Ideas ───────────────────────────────────────────────────────────────
  async function generateIdeas() {
    if (!keywords.trim() || !personaId) return;
    generatingIdeas = true;
    ideasError = '';
    try {
      const resp = await generation.generateIdeas({
        persona_id: personaId,
        keywords: keywords.trim(),
        platform: platforms.length === 2 ? 'both' : (platforms[0] ?? 'linkedin'),
        n: 10,
      });
      const fresh: Idea[] = resp.ideas.map((i: { angle: string; rationale: string; platform: string }) => ({
        id: uid(),
        angle: i.angle,
        rationale: i.rationale,
        platform: (i.platform === 'instagram' ? 'instagram' : 'linkedin') as Platform,
        selected: true,
        status: 'pending' as IdeaStatus,
      }));
      ideas = [...ideas, ...fresh];
    } catch (e) {
      ideasError = e instanceof Error ? e.message : String(e);
    } finally {
      generatingIdeas = false;
    }
  }

  function addManualIdea() {
    if (!newIdeaText.trim()) return;
    ideas = [...ideas, {
      id: uid(),
      angle: newIdeaText.trim(),
      rationale: '',
      platform: platforms[0] ?? 'linkedin',
      selected: true,
      status: 'pending',
    }];
    newIdeaText = '';
    addingIdea = false;
  }

  function removeIdea(id: string) {
    ideas = ideas.filter(i => i.id !== id);
  }

  function toggleAll(v: boolean) {
    ideas = ideas.map(i => ({ ...i, selected: v }));
  }

  $: selectedIdeas = ideas.filter(i => i.selected);

  // ─── Platforms multi-select ──────────────────────────────────────────────
  function togglePlatform(p: Platform) {
    if (platforms.includes(p)) {
      if (platforms.length > 1) platforms = platforms.filter(x => x !== p);
    } else {
      platforms = [...platforms, p];
    }
  }

  // ─── Bulk generation ─────────────────────────────────────────────────────
  async function createQuickPlanning() {
    if (!personaId) return;
    const now = new Date();
    const end = new Date(now);
    end.setDate(end.getDate() + 90);
    const p = await api.plannings.create({ persona_id: personaId, date_debut: now.toISOString(), date_fin: end.toISOString() });
    plannings = [p, ...plannings];
    planningId = p.id;
  }

  async function bulkGenerate() {
    if (!selectedIdeas.length || !personaId || !planningId) return;
    bulkGenerating = true;
    bulkError = '';
    const tasks: Array<{ idea: Idea; platform: Platform }> = [];
    for (const idea of selectedIdeas) {
      for (const p of platforms) {
        tasks.push({ idea, platform: p });
      }
    }
    bulkTotal = tasks.length;
    bulkProgress = 0;

    const baseDate = new Date(startDate || new Date());
    let dayOffset = 0;
    let lastIdeaId = '';

    for (const { idea, platform } of tasks) {
      if (idea.id !== lastIdeaId) {
        if (lastIdeaId) dayOffset += intervalDays;
        lastIdeaId = idea.id;
      }
      const scheduledAt = new Date(baseDate);
      scheduledAt.setDate(scheduledAt.getDate() + dayOffset);

      const tempId = uid();
      const placeholder: GenPost = {
        id: tempId,
        post_id: '',
        idea_id: idea.id,
        platform,
        text: '',
        image_url: '',
        scheduled_for: scheduledAt.toISOString(),
        status: 'draft',
        comment: '',
        saving: false,
        regenerating: false,
        expanded: false,
      };
      posts = [...posts, placeholder];

      try {
        const resp = await generation.generate({
          planning_id: planningId,
          persona_id: personaId,
          angle_editorial: idea.angle,
          format,
          platform,
        });

        let imageUrl = resp.image_url ?? '';
        if (format !== 'text_only') {
          const persona = personas.find(p => p.id === personaId);
          const buTheme = BU_THEMES[persona?.bu ?? 'noisyless'];
          const visualTitle = resp.visual_headline || idea.angle.slice(0, 80);
          const bodySnippet = platform === 'instagram'
            ? ''
            : resp.text.split('\n').filter((l: string) => l.trim()).slice(0, 2).join(' ').slice(0, 200);
          try {
            const imgResp = await fetch(`${PUBLIC_CAROUSEL_URL}/api/v1/image/generate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                bu: persona?.bu ?? 'noisyless',
                platform,
                title: visualTitle,
                body: bodySnippet,
                background_color: buTheme.bg,
                text_color: buTheme.text,
              }),
            });
            const imgData = await imgResp.json();
            imageUrl = imgData.image_url || imageUrl;
          } catch { /* keep existing */ }
        }

        posts = posts.map(p => p.id === tempId ? {
          ...p,
          post_id: resp.post_id,
          text: resp.text,
          image_url: imageUrl,
        } : p);
      } catch (e) {
        posts = posts.map(p => p.id === tempId ? { ...p, text: '⚠ Erreur de génération', status: 'draft' } : p);
      }
      bulkProgress++;
    }
    bulkGenerating = false;
  }

  // ─── Card actions ─────────────────────────────────────────────────────────
  async function validatePost(p: GenPost) {
    if (!p.post_id) return;
    posts = posts.map(x => x.id === p.id ? { ...x, saving: true } : x);
    try {
      await api.posts.update(p.post_id, {
        text: p.text,
        status: 'scheduled',
        scheduled_for: p.scheduled_for,
      });
      posts = posts.map(x => x.id === p.id ? { ...x, saving: false, status: 'scheduled' } : x);
    } catch (e) {
      posts = posts.map(x => x.id === p.id ? { ...x, saving: false } : x);
    }
  }

  async function regeneratePost(p: GenPost) {
    if (!p.post_id) return;
    const idea = ideas.find(i => i.id === p.idea_id);
    if (!idea) return;
    posts = posts.map(x => x.id === p.id ? { ...x, regenerating: true } : x);
    try {
      const resp = await generation.generate({
        planning_id: planningId,
        persona_id: personaId,
        angle_editorial: idea.angle + (p.comment ? `\n\nNote : ${p.comment}` : ''),
        format,
        platform: p.platform,
      });
      let imageUrl = resp.image_url ?? '';
      if (format !== 'text_only') {
        const persona = personas.find(pe => pe.id === personaId);
        const buTheme = BU_THEMES[persona?.bu ?? 'noisyless'];
        const visualTitle = resp.visual_headline || idea?.angle.slice(0, 80) || '';
        const bodySnippet = p.platform === 'instagram'
          ? ''
          : resp.text.split('\n').filter((l: string) => l.trim()).slice(0, 2).join(' ').slice(0, 200);
        try {
          const imgResp = await fetch(`${PUBLIC_CAROUSEL_URL}/api/v1/image/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              bu: persona?.bu ?? 'noisyless',
              platform: p.platform,
              title: visualTitle,
              body: bodySnippet,
              background_color: buTheme.bg,
              text_color: buTheme.text,
            }),
          });
          const imgData = await imgResp.json();
          imageUrl = imgData.image_url || imageUrl;
        } catch { /* keep existing */ }
      }
      posts = posts.map(x => x.id === p.id ? { ...x, regenerating: false, text: resp.text, image_url: imageUrl, comment: '' } : x);
    } catch {
      posts = posts.map(x => x.id === p.id ? { ...x, regenerating: false } : x);
    }
  }

  function deletePost(id: string) {
    posts = posts.filter(p => p.id !== id);
  }

  $: scheduledCount = posts.filter(p => p.status === 'scheduled').length;
</script>

<svelte:head><title>Composer — SaaS RSE</title></svelte:head>

<div class="studio">
  <!-- HEADER -->
  <div class="studio-header">
    <div class="studio-title">
      <span class="studio-icon">⚡</span>
      <div>
        <h1>Studio de contenu</h1>
        <p class="studio-sub">Générez et planifiez vos publications en masse</p>
      </div>
    </div>
    {#if scheduledCount > 0}
      <div class="badge-success">{scheduledCount} post{scheduledCount > 1 ? 's' : ''} planifié{scheduledCount > 1 ? 's' : ''}</div>
    {/if}
  </div>

  {#if error}<div class="error-banner">{error}</div>{/if}

  {#if loading}
    <div class="dark-loading">Chargement…</div>
  {:else}

  <!-- ═══ SECTION 1 — IDÉES ════════════════════════════════════════════════ -->
  <section class="studio-section">
    <div class="section-head">
      <h2><span class="step-num">1</span> Idées éditoriales</h2>
      <span class="ideas-count">{ideas.length} idée{ideas.length !== 1 ? 's' : ''}</span>
    </div>

    <!-- Config rapide persona + plateformes pour la génération d'idées -->
    <div class="ideas-config">
      <div class="field-group">
        <label class="dark-label">Persona</label>
        <select bind:value={personaId} class="dark-select">
          {#each personas as p}
            <option value={p.id}>{p.nom} — {p.bu}</option>
          {/each}
        </select>
      </div>
      <div class="field-group">
        <label class="dark-label">Plateformes</label>
        <div class="plat-checks">
          {#each ALL_PLATFORMS as p}
            <button
              class="plat-check"
              class:active={platforms.includes(p)}
              style="--plat-color: {PLAT_COLORS[p]}"
              on:click={() => togglePlatform(p)}
            >{p === 'linkedin' ? '💼 LinkedIn' : '📸 Instagram'}</button>
          {/each}
        </div>
      </div>
    </div>

    <!-- Keyword generator -->
    <div class="keyword-bar">
      <input
        class="dark-input kw-input"
        bind:value={keywords}
        placeholder="Mots-clés : acoustique, open space, concentration, bruit…"
        on:keydown={(e) => e.key === 'Enter' && generateIdeas()}
      />
      <button class="btn-gen" on:click={generateIdeas} disabled={generatingIdeas || !keywords.trim() || !personaId}>
        {#if generatingIdeas}
          <span class="spin-xs"></span> Génération…
        {:else}
          ✨ Générer 10 idées
        {/if}
      </button>
      <button class="btn-secondary-dark" on:click={() => addingIdea = !addingIdea}>
        + Ajouter
      </button>
    </div>

    {#if ideasError}<div class="error-inline">{ideasError}</div>{/if}

    {#if addingIdea}
      <div class="add-idea-bar">
        <input class="dark-input" bind:value={newIdeaText} placeholder="Ton angle éditorial…" on:keydown={(e) => e.key === 'Enter' && addManualIdea()} />
        <button class="btn-gen btn-sm" on:click={addManualIdea}>Ajouter</button>
        <button class="btn-ghost" on:click={() => addingIdea = false}>Annuler</button>
      </div>
    {/if}

    <!-- Ideas table -->
    {#if ideas.length > 0}
      <div class="ideas-table-wrap">
        <table class="ideas-table">
          <thead>
            <tr>
              <th class="col-check">
                <input type="checkbox"
                  checked={selectedIdeas.length === ideas.length && ideas.length > 0}
                  indeterminate={selectedIdeas.length > 0 && selectedIdeas.length < ideas.length}
                  on:change={(e) => toggleAll(e.currentTarget.checked)}
                />
              </th>
              <th class="col-angle">Angle éditorial</th>
              <th class="col-plat">Plateforme</th>
              <th class="col-act"></th>
            </tr>
          </thead>
          <tbody>
            {#each ideas as idea (idea.id)}
              <tr class:selected={idea.selected}>
                <td class="col-check">
                  <input type="checkbox" bind:checked={idea.selected} />
                </td>
                <td class="col-angle">
                  <div class="idea-angle">{idea.angle}</div>
                  {#if idea.rationale}
                    <div class="idea-rationale">{idea.rationale}</div>
                  {/if}
                </td>
                <td class="col-plat">
                  <span class="plat-badge" style="background: {PLAT_COLORS[idea.platform]}22; color: {PLAT_COLORS[idea.platform]}">
                    {idea.platform}
                  </span>
                </td>
                <td class="col-act">
                  <button class="btn-icon" on:click={() => removeIdea(idea.id)} title="Supprimer">✕</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <div class="selection-bar">
        <span>{selectedIdeas.length} idée{selectedIdeas.length !== 1 ? 's' : ''} sélectionnée{selectedIdeas.length !== 1 ? 's' : ''}</span>
        {#if selectedIdeas.length > 0}
          <button class="btn-ghost-sm" on:click={() => toggleAll(false)}>Tout désélectionner</button>
        {:else}
          <button class="btn-ghost-sm" on:click={() => toggleAll(true)}>Tout sélectionner</button>
        {/if}
      </div>
    {:else}
      <div class="ideas-empty">
        <span>💡</span>
        <p>Entre des mots-clés et génère des idées, ou ajoute-les manuellement.</p>
      </div>
    {/if}
  </section>

  <!-- ═══ SECTION 2 — PARAMÈTRES ══════════════════════════════════════════ -->
  {#if ideas.length > 0}
  <section class="studio-section">
    <div class="section-head">
      <h2><span class="step-num">2</span> Paramètres de génération</h2>
      {#if selectedIdeas.length > 0}
        <span class="ideas-count">{selectedIdeas.length * platforms.length} publication{selectedIdeas.length * platforms.length > 1 ? 's' : ''} à générer</span>
      {/if}
    </div>

    <div class="params-grid">
      <div class="field-group">
        <label class="dark-label">Planning</label>
        {#if plannings.length === 0}
          <button class="btn-secondary-dark" on:click={createQuickPlanning} disabled={!personaId}>
            Créer un planning 90 jours
          </button>
        {:else}
          <select bind:value={planningId} class="dark-select">
            {#each plannings as pl}
              <option value={pl.id}>
                {new Date(pl.date_debut).toLocaleDateString('fr-FR')} → {new Date(pl.date_fin).toLocaleDateString('fr-FR')}
              </option>
            {/each}
          </select>
        {/if}
      </div>

      <div class="field-group">
        <label class="dark-label">Format</label>
        <div class="format-group">
          {#each FORMAT_OPTS as f}
            <button
              class="format-pill"
              class:active={format === f.id}
              on:click={() => format = f.id}
            >{f.label}</button>
          {/each}
        </div>
      </div>

      <div class="field-group">
        <label class="dark-label">Intervalle entre chaque idée</label>
        <div class="interval-row">
          <span>Tous les</span>
          <input type="number" class="dark-input num-input" bind:value={intervalDays} min="1" max="30" />
          <span>jours</span>
        </div>
      </div>

      <div class="field-group">
        <label class="dark-label">Date de départ</label>
        <input type="datetime-local" class="dark-input" bind:value={startDate} />
      </div>
    </div>

    {#if bulkError}<div class="error-inline">{bulkError}</div>{/if}

    <button
      class="btn-generate-all"
      on:click={bulkGenerate}
      disabled={bulkGenerating || selectedIdeas.length === 0 || !planningId}
    >
      {#if bulkGenerating}
        <span class="spin-xs"></span>
        Génération {bulkProgress}/{bulkTotal}…
        <div class="progress-bar">
          <div class="progress-fill" style="width: {bulkTotal > 0 ? (bulkProgress/bulkTotal*100) : 0}%"></div>
        </div>
      {:else}
        ✨ Générer {selectedIdeas.length * platforms.length} publication{selectedIdeas.length * platforms.length > 1 ? 's' : ''}
      {/if}
    </button>
  </section>
  {/if}

  <!-- ═══ SECTION 3 — APERÇU PUBLICATIONS ════════════════════════════════ -->
  {#if posts.length > 0}
  <section class="studio-section">
    <div class="section-head">
      <h2><span class="step-num">3</span> Publications générées</h2>
      <div class="head-actions">
        <span class="ideas-count">{scheduledCount}/{posts.length} validées</span>
        {#if posts.filter(p => p.status !== 'scheduled' && p.post_id).length > 0}
          <button class="btn-ghost-sm" on:click={async () => { for (const p of posts.filter(x => x.status !== 'scheduled' && x.post_id)) await validatePost(p); }}>
            ✅ Valider tout
          </button>
        {/if}
      </div>
    </div>

    <div class="posts-grid">
      {#each posts as post (post.id)}
        {@const idea = ideas.find(i => i.id === post.idea_id)}
        <div class="post-card" class:validated={post.status === 'scheduled'}>
          <!-- Image zone -->
          <div class="card-image">
            {#if post.regenerating || (post.post_id === '' && !post.text)}
              <div class="img-loading">
                <div class="img-pulse"></div>
                <span>Génération…</span>
              </div>
            {:else if post.image_url}
              <img src={post.image_url} alt="post visual" />
            {:else}
              <div class="img-placeholder" style="background: linear-gradient(135deg, {BU_COLORS[personas.find(p => p.id === personaId)?.bu ?? 'noisyless']?.bg ?? '#2A2A38'} 0%, #1A1A2E 100%)">
                <span class="img-icon">{post.platform === 'linkedin' ? '💼' : '📸'}</span>
                <span class="img-label">{FORMAT_OPTS.find(f => f.id === format)?.label ?? ''}</span>
              </div>
            {/if}
            <!-- Platform + date overlay -->
            <div class="card-meta-overlay">
              <span class="plat-badge-sm" style="background: {PLAT_COLORS[post.platform]}">
                {post.platform === 'linkedin' ? '💼' : '📸'}
              </span>
              <span class="date-badge">
                {new Date(post.scheduled_for).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}
              </span>
            </div>
            {#if post.status === 'scheduled'}
              <div class="validated-overlay">✅</div>
            {/if}
          </div>

          <!-- Text content -->
          <div class="card-content">
            {#if idea}
              <div class="card-angle">{idea.angle}</div>
            {/if}
            {#if post.text && post.text !== '⚠ Erreur de génération'}
              <div class="card-text" class:expanded={post.expanded}>
                {post.text}
              </div>
              <button class="expand-btn" on:click={() => post.expanded = !post.expanded}>
                {post.expanded ? '↑ Réduire' : '↓ Voir tout'}
              </button>
              <div class="char-count-dark" class:over={post.text.length > (post.platform === 'linkedin' ? 3000 : 2200)}>
                {post.text.length} car.
              </div>
            {:else if post.text === '⚠ Erreur de génération'}
              <div class="gen-error">⚠ Échec de génération</div>
            {/if}
          </div>

          <!-- Comment + Actions -->
          <div class="card-footer">
            <textarea
              class="comment-input"
              bind:value={post.comment}
              placeholder="Commentaire pour la regénération…"
              rows="2"
            ></textarea>
            <div class="card-actions">
              <button
                class="btn-validate"
                class:done={post.status === 'scheduled'}
                on:click={() => validatePost(post)}
                disabled={post.saving || !post.post_id || post.status === 'scheduled'}
              >
                {#if post.saving}…
                {:else if post.status === 'scheduled'}✅ Validé
                {:else}✅ Valider
                {/if}
              </button>
              <button
                class="btn-regen"
                on:click={() => regeneratePost(post)}
                disabled={post.regenerating || !post.post_id}
              >
                {post.regenerating ? '…' : '↺ Regénérer'}
              </button>
              <button class="btn-del" on:click={() => deletePost(post.id)} title="Supprimer">✕</button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  </section>
  {/if}

  {/if}<!-- end if !loading -->
</div>

<style>
  /* ── Dark theme scope ──────────────────────────────────────────────────── */
  :global(body) { background: #0D0D14 !important; color: #E2E2F0 !important; }
  :global(.layout) { background: #0D0D14 !important; }
  :global(nav.navbar) {
    background: #141420 !important;
    border-bottom-color: #2E2E42 !important;
  }
  :global(nav.navbar a) { color: #9090B0 !important; }
  :global(nav.navbar a.active) { color: #6C63FF !important; border-bottom-color: #6C63FF !important; }

  .studio {
    padding: 28px 32px;
    min-height: 100vh;
    background: #0D0D14;
    color: #E2E2F0;
  }

  /* ── Header ──────────────────────────────────────────────────────────── */
  .studio-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 32px;
  }
  .studio-title { display: flex; align-items: center; gap: 16px; }
  .studio-icon {
    font-size: 32px;
    background: linear-gradient(135deg, #6C63FF, #A78BFA);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  h1 { font-size: 26px; font-weight: 800; margin: 0; background: linear-gradient(135deg, #fff 40%, #A78BFA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .studio-sub { font-size: 13px; color: #5A5A7A; margin: 2px 0 0; }

  .badge-success {
    background: #0F4F2E;
    color: #34D399;
    border: 1px solid #1B7A4A;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
  }

  /* ── Sections ─────────────────────────────────────────────────────────── */
  .studio-section {
    background: #141420;
    border: 1px solid #2E2E42;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
  }
  .section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
  }
  .section-head h2 {
    font-size: 16px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0;
    color: #E2E2F0;
  }
  .step-num {
    width: 26px; height: 26px;
    background: #6C63FF;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 800;
    color: #fff;
    flex-shrink: 0;
  }
  .ideas-count { font-size: 12px; color: #5A5A7A; }

  /* ── Ideas config ─────────────────────────────────────────────────────── */
  .ideas-config { display: flex; gap: 20px; margin-bottom: 16px; }
  .field-group { display: flex; flex-direction: column; gap: 6px; }
  .dark-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #5A5A7A; }

  /* ── Dark inputs ──────────────────────────────────────────────────────── */
  .dark-input, .dark-select {
    background: #1E1E2E;
    border: 1px solid #2E2E42;
    border-radius: 8px;
    padding: 8px 12px;
    color: #E2E2F0;
    font-family: inherit;
    font-size: 13px;
    transition: border-color 0.15s;
  }
  .dark-input:focus, .dark-select:focus {
    outline: none;
    border-color: #6C63FF;
    box-shadow: 0 0 0 3px rgba(108,99,255,0.15);
  }
  .dark-select option { background: #1E1E2E; }

  /* ── Platform checks ──────────────────────────────────────────────────── */
  .plat-checks { display: flex; gap: 8px; }
  .plat-check {
    padding: 6px 14px;
    border-radius: 6px;
    border: 1px solid #2E2E42;
    background: #1E1E2E;
    color: #6B6B8A;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.12s;
  }
  .plat-check.active {
    background: color-mix(in srgb, var(--plat-color) 15%, #1E1E2E);
    border-color: var(--plat-color);
    color: var(--plat-color);
  }

  /* ── Keyword bar ──────────────────────────────────────────────────────── */
  .keyword-bar { display: flex; gap: 10px; margin-bottom: 12px; }
  .kw-input { flex: 1; }

  .btn-gen {
    background: linear-gradient(135deg, #6C63FF, #8B5CF6);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
    display: flex; align-items: center; gap: 6px;
    transition: opacity 0.15s;
  }
  .btn-gen:disabled { opacity: 0.4; cursor: default; }
  .btn-gen.btn-sm { padding: 6px 14px; font-size: 12px; }

  .btn-secondary-dark {
    background: #1E1E2E;
    border: 1px solid #2E2E42;
    color: #A0A0C0;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    cursor: pointer;
    transition: border-color 0.15s;
  }
  .btn-secondary-dark:hover { border-color: #6C63FF; color: #E2E2F0; }
  .btn-secondary-dark:disabled { opacity: 0.4; cursor: default; }

  .btn-ghost { background: none; border: none; color: #5A5A7A; cursor: pointer; font-size: 13px; }
  .btn-ghost:hover { color: #E2E2F0; }
  .btn-ghost-sm { background: none; border: none; color: #6C63FF; cursor: pointer; font-size: 12px; }
  .btn-ghost-sm:hover { text-decoration: underline; }
  .btn-icon { background: none; border: none; color: #3A3A52; cursor: pointer; font-size: 14px; padding: 4px 6px; border-radius: 4px; }
  .btn-icon:hover { color: #EF4444; background: #2A1A1A; }

  .add-idea-bar { display: flex; gap: 10px; margin-bottom: 12px; }
  .add-idea-bar .dark-input { flex: 1; }

  /* ── Ideas table ──────────────────────────────────────────────────────── */
  .ideas-table-wrap { overflow-x: auto; border-radius: 10px; border: 1px solid #2E2E42; }
  .ideas-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .ideas-table thead { background: #1A1A28; }
  .ideas-table th { padding: 10px 14px; text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #5A5A7A; }
  .ideas-table td { padding: 10px 14px; border-top: 1px solid #1E1E2E; vertical-align: top; }
  .ideas-table tr.selected { background: rgba(108,99,255,0.04); }
  .ideas-table tr:hover td { background: #1A1A28; }
  .col-check { width: 36px; }
  .col-angle { }
  .col-plat { width: 120px; }
  .col-act { width: 40px; }
  .idea-angle { font-weight: 600; color: #D0D0E8; line-height: 1.4; }
  .idea-rationale { font-size: 11px; color: #5A5A7A; margin-top: 3px; line-height: 1.4; }

  .plat-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }
  .plat-badge-sm { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; }

  .selection-bar { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; font-size: 12px; color: #5A5A7A; }

  .ideas-empty { text-align: center; padding: 40px; color: #3A3A52; display: flex; flex-direction: column; align-items: center; gap: 8px; font-size: 14px; }
  .ideas-empty span { font-size: 32px; }

  /* ── Params grid ──────────────────────────────────────────────────────── */
  .params-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 16px; margin-bottom: 20px; }

  .format-group { display: flex; gap: 6px; }
  .format-pill {
    padding: 6px 14px;
    border-radius: 6px;
    border: 1px solid #2E2E42;
    background: #1E1E2E;
    color: #6B6B8A;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.12s;
  }
  .format-pill.active { background: rgba(108,99,255,0.15); border-color: #6C63FF; color: #A78BFA; }

  .interval-row { display: flex; align-items: center; gap: 8px; font-size: 13px; }
  .num-input { width: 60px; text-align: center; }

  /* ── Generate all button ─────────────────────────────────────────────── */
  .btn-generate-all {
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, #6C63FF 0%, #8B5CF6 50%, #A78BFA 100%);
    border: none;
    border-radius: 10px;
    color: #fff;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    transition: opacity 0.15s;
  }
  .btn-generate-all:disabled { opacity: 0.6; cursor: default; }
  .btn-generate-all:not(:disabled):hover { filter: brightness(1.1); }

  .progress-bar { position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background: rgba(255,255,255,0.2); }
  .progress-fill { height: 100%; background: #fff; transition: width 0.3s ease; }

  /* ── Posts grid ───────────────────────────────────────────────────────── */
  .posts-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
  .head-actions { display: flex; align-items: center; gap: 12px; }

  .post-card {
    background: #1A1A28;
    border: 1px solid #2E2E42;
    border-radius: 14px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: border-color 0.2s;
  }
  .post-card.validated { border-color: #1B7A4A; }

  /* Card image */
  .card-image { position: relative; aspect-ratio: 1; background: #1E1E2E; flex-shrink: 0; overflow: hidden; }
  .card-image img { width: 100%; height: 100%; object-fit: cover; }
  .img-loading {
    width: 100%; height: 100%;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 12px; color: #5A5A7A; font-size: 12px;
  }
  .img-pulse {
    width: 36px; height: 36px; border-radius: 50%;
    background: linear-gradient(135deg, #6C63FF, #8B5CF6);
    animation: pulse 1.2s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100% { transform: scale(1); opacity:1; } 50% { transform: scale(1.3); opacity:0.4; } }

  .img-placeholder {
    width: 100%; height: 100%;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 8px;
  }
  .img-icon { font-size: 32px; }
  .img-label { font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 1px; }

  .card-meta-overlay {
    position: absolute; top: 10px; left: 10px; right: 10px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .date-badge {
    background: rgba(0,0,0,0.6);
    color: #fff;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    backdrop-filter: blur(4px);
  }
  .validated-overlay {
    position: absolute; inset: 0;
    background: rgba(0,80,40,0.3);
    display: flex; align-items: center; justify-content: center;
    font-size: 40px;
    backdrop-filter: blur(2px);
  }

  /* Card content */
  .card-content { padding: 14px; flex: 1; display: flex; flex-direction: column; gap: 6px; }
  .card-angle { font-size: 11px; font-weight: 700; color: #6C63FF; text-transform: uppercase; letter-spacing: 0.4px; line-height: 1.3; }
  .card-text {
    font-size: 12px;
    color: #A0A0C0;
    line-height: 1.6;
    max-height: 80px;
    overflow: hidden;
    white-space: pre-wrap;
    transition: max-height 0.3s;
  }
  .card-text.expanded { max-height: 400px; }
  .expand-btn { background: none; border: none; color: #5A5A7A; font-size: 11px; cursor: pointer; padding: 0; text-align: left; }
  .expand-btn:hover { color: #6C63FF; }
  .char-count-dark { font-size: 10px; color: #3A3A52; }
  .char-count-dark.over { color: #EF4444; }
  .gen-error { font-size: 12px; color: #EF4444; }

  /* Card footer */
  .card-footer { padding: 12px 14px; border-top: 1px solid #2E2E42; display: flex; flex-direction: column; gap: 8px; }
  .comment-input {
    width: 100%;
    background: #0D0D14;
    border: 1px solid #2E2E42;
    border-radius: 6px;
    padding: 6px 10px;
    color: #A0A0C0;
    font-family: inherit;
    font-size: 11px;
    resize: none;
  }
  .comment-input:focus { outline: none; border-color: #6C63FF; }
  .comment-input::placeholder { color: #3A3A52; }

  .card-actions { display: flex; gap: 6px; }
  .btn-validate {
    flex: 1;
    padding: 7px 10px;
    background: #0F3D20;
    border: 1px solid #1B5E3A;
    border-radius: 6px;
    color: #34D399;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.12s;
  }
  .btn-validate:hover:not(:disabled):not(.done) { background: #1B5E3A; }
  .btn-validate:disabled { opacity: 0.4; cursor: default; }
  .btn-validate.done { background: #1B5E3A; border-color: #34D399; }

  .btn-regen {
    padding: 7px 10px;
    background: #1E1A2E;
    border: 1px solid #3A2E5A;
    border-radius: 6px;
    color: #A78BFA;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.12s;
  }
  .btn-regen:hover:not(:disabled) { background: #2A1E48; border-color: #6C63FF; }
  .btn-regen:disabled { opacity: 0.4; cursor: default; }

  .btn-del {
    padding: 7px 10px;
    background: none;
    border: 1px solid #2E2E42;
    border-radius: 6px;
    color: #3A3A52;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.12s;
  }
  .btn-del:hover { background: #2A1A1A; border-color: #EF4444; color: #EF4444; }

  /* Misc */
  .error-banner { background: #2A1A1A; border: 1px solid #EF4444; color: #FCA5A5; border-radius: 8px; padding: 10px 14px; font-size: 13px; margin-bottom: 16px; }
  .error-inline { background: #2A1A1A; border: 1px solid #7F1D1D; color: #FCA5A5; border-radius: 6px; padding: 8px 12px; font-size: 12px; margin-bottom: 10px; }
  .dark-loading { color: #5A5A7A; padding: 60px; text-align: center; }

  .spin-xs {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
