<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { Persona, BU, Account, Platform, AccountKind } from '$lib/types';

  let personas: Persona[] = [];
  let accounts: Account[] = [];
  let loading = true;
  let error = '';

  const PLATFORMS: Platform[] = ['linkedin', 'instagram', 'facebook', 'tiktok'];
  const KIND_LABELS: Record<AccountKind, string> = {
    personal: 'Profil personnel',
    company_page: 'Page entreprise',
    business_account: 'Compte pro',
  };
  const PLATFORM_SHORT: Record<Platform, string> = { linkedin: 'in', instagram: 'ig', facebook: 'fb', tiktok: 'tk' };

  // Form state
  let showForm = false;
  let editingId: string | null = null;
  let saving = false;
  let formError = '';

  const BUS: BU[] = ['noisyless', 'afluxo', 'mbhrep'];
  const BU_LABELS: Record<BU, string> = { noisyless: 'Noisyless', afluxo: 'Afluxo', mbhrep: 'MBHREP' };

  let form = defaultForm();

  function defaultForm() {
    return {
      bu: 'noisyless' as BU,
      nom: '',
      besoins: '',
      frustrations: '',
      cible: '',
      ton: '',
      mots_interdits: '',
      longueur_cible: 1500,
      emojis: '',
    };
  }

  onMount(async () => {
    await loadPersonas();
  });

  async function loadPersonas() {
    loading = true;
    error = '';
    try {
      [personas, accounts] = await Promise.all([api.personas.list(), api.accounts.list()]);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  function accountsOf(personaId: string): Account[] {
    return accounts.filter(a => a.persona_id === personaId);
  }

  // --- Comptes de publication ---
  let accountFormFor: string | null = null;
  let accountSaving = false;
  let accountForm = defaultAccountForm();

  function defaultAccountForm() {
    return {
      platform: 'linkedin' as Platform,
      kind: 'company_page' as AccountKind,
      identity_name: '',
      page_url: '',
      asset_id: '',
    };
  }

  function startAddAccount(personaId: string) {
    accountFormFor = personaId;
    accountForm = defaultAccountForm();
  }

  async function saveAccount(personaId: string) {
    accountSaving = true;
    try {
      const created = await api.accounts.create({
        persona_id: personaId,
        platform: accountForm.platform,
        kind: accountForm.kind,
        identity_name: accountForm.identity_name.trim() || null,
        page_url: accountForm.page_url.trim() || null,
        asset_id: accountForm.asset_id.trim() || null,
      });
      accounts = [...accounts, created];
      accountFormFor = null;
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      accountSaving = false;
    }
  }

  async function toggleAccount(a: Account) {
    try {
      const updated = await api.accounts.update(a.id, { enabled: !a.enabled });
      accounts = accounts.map(x => x.id === a.id ? updated : x);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  async function deleteAccount(a: Account) {
    if (!confirm(`Supprimer le compte ${a.identity_name || a.platform} ?`)) return;
    try {
      await api.accounts.delete(a.id);
      accounts = accounts.filter(x => x.id !== a.id);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  function startCreate() {
    editingId = null;
    form = defaultForm();
    showForm = true;
    formError = '';
  }

  function startEdit(p: Persona) {
    editingId = p.id;
    const cb = p.charte_branding as Record<string, unknown>;
    form = {
      bu: p.bu as BU,
      nom: p.nom,
      besoins: p.besoins,
      frustrations: p.frustrations,
      cible: p.cible,
      ton: (cb.ton as string) ?? '',
      mots_interdits: Array.isArray(cb.mots_interdits) ? (cb.mots_interdits as string[]).join(', ') : '',
      longueur_cible: (cb.longueur_cible as number) ?? 1500,
      emojis: Array.isArray(cb.emojis) ? (cb.emojis).join(' ') : '',
    };
    showForm = true;
    formError = '';
  }

  async function save() {
    saving = true;
    formError = '';
    const payload = {
      bu: form.bu,
      nom: form.nom.trim(),
      besoins: form.besoins.trim(),
      frustrations: form.frustrations.trim(),
      cible: form.cible.trim(),
      charte_branding: {
        ton: form.ton.trim(),
        mots_interdits: form.mots_interdits.split(',').map(s => s.trim()).filter(Boolean),
        longueur_cible: form.longueur_cible,
        emojis: form.emojis.split(/\s+/).filter(Boolean),
      },
    };
    try {
      if (editingId) {
        await api.personas.update(editingId, payload);
      } else {
        await api.personas.create(payload);
      }
      showForm = false;
      await loadPersonas();
    } catch (e) {
      formError = e instanceof Error ? e.message : String(e);
    } finally {
      saving = false;
    }
  }

  async function deletePersona(id: string, nom: string) {
    if (!confirm(`Supprimer "${nom}" ? Cette action est irréversible.`)) return;
    try {
      await api.personas.delete(id);
      personas = personas.filter(p => p.id !== id);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  let expanded: string | null = null;
</script>

<svelte:head><title>Personas — SaaS RSE</title></svelte:head>

<main class="page">
  <div class="page-header">
    <div>
      <h1>Personas</h1>
      <p class="subtitle">{personas.length} persona{personas.length !== 1 ? 's' : ''} · charte éditoriale par BU</p>
    </div>
    <button class="btn btn-primary" on:click={startCreate}>+ Nouveau persona</button>
  </div>

  {#if error}<div class="error-banner">{error}</div>{/if}

  {#if loading}
    <div class="loading">Chargement…</div>
  {:else if personas.length === 0 && !showForm}
    <div class="empty-state">
      <div class="icon">👤</div>
      <p>Aucun persona. Commence par <a href="/grillme">GrilledMe</a> ou crée-en un manuellement.</p>
    </div>
  {:else}
    <div class="persona-list">
      {#each personas as p (p.id)}
        {@const cb = p.charte_branding}
        <div class="persona-card" class:open={expanded === p.id}>
          <div class="persona-header" on:click={() => expanded = expanded === p.id ? null : p.id} role="button" tabindex="0" on:keydown={(e) => e.key === 'Enter' && (expanded = expanded === p.id ? null : p.id)}>
            <div class="persona-title">
              <span class="bu-tag bu-{p.bu}">{BU_LABELS[p.bu]}</span>
              <span class="persona-nom">{p.nom}</span>
            </div>
            <div class="persona-actions">
              <button class="btn btn-secondary btn-sm" on:click|stopPropagation={() => startEdit(p)}>Modifier</button>
              <button class="btn btn-danger btn-sm" on:click|stopPropagation={() => deletePersona(p.id, p.nom)}>Supprimer</button>
              <span class="chevron" class:rotated={expanded === p.id}>▾</span>
            </div>
          </div>

          {#if expanded === p.id}
            <div class="persona-body">
              <div class="grid-2">
                <div class="field">
                  <div class="field-label">Cible</div>
                  <div class="field-value">{p.cible}</div>
                </div>
                <div class="field">
                  <div class="field-label">Besoins</div>
                  <div class="field-value">{p.besoins}</div>
                </div>
                <div class="field">
                  <div class="field-label">Frustrations</div>
                  <div class="field-value">{p.frustrations}</div>
                </div>
                <div class="field">
                  <div class="field-label">Charte éditoriale</div>
                  <div class="charte">
                    {#if cb.ton}<div class="charte-row"><span class="charte-key">Ton</span><span>{cb.ton}</span></div>{/if}
                    {#if Array.isArray(cb.mots_interdits) && cb.mots_interdits.length}
                      <div class="charte-row">
                        <span class="charte-key">Mots interdits</span>
                        <span class="tags-row">
                          {#each cb.mots_interdits as mot}
                            <span class="tag-bad">{mot}</span>
                          {/each}
                        </span>
                      </div>
                    {/if}
                    {#if cb.longueur_cible}
                      <div class="charte-row"><span class="charte-key">Longueur</span><span>{cb.longueur_cible} car.</span></div>
                    {/if}
                    {#if Array.isArray(cb.emojis) && cb.emojis.length}
                      <div class="charte-row"><span class="charte-key">Emojis</span><span>{Array.isArray(cb.emojis) ? cb.emojis.join(' ') : ''}</span></div>
                    {/if}
                  </div>
                </div>
              </div>
              <!-- Comptes de publication -->
              <div class="pub-pages">
                <div class="pub-section-head">
                  <span class="field-label">Comptes de publication</span>
                  <button class="btn btn-secondary btn-sm" on:click={() => startAddAccount(p.id)}>+ Compte</button>
                </div>
                {#each accountsOf(p.id) as a (a.id)}
                  <div class="pub-page-row" class:disabled={!a.enabled}>
                    <span class="pub-platform {a.platform}">{PLATFORM_SHORT[a.platform]}</span>
                    <span class="pub-kind">{KIND_LABELS[a.kind]}</span>
                    <span class="pub-identity">{a.identity_name || '—'}</span>
                    {#if a.page_url}
                      <a class="pub-url" href={a.page_url} target="_blank" rel="noopener">{a.page_url.replace(/^https:\/\/(www\.)?/, '').replace(/\/$/, '')}</a>
                    {/if}
                    <span class="pub-row-actions">
                      <button class="link-btn" on:click={() => toggleAccount(a)}>{a.enabled ? 'Désactiver' : 'Activer'}</button>
                      <button class="link-btn danger" on:click={() => deleteAccount(a)}>Supprimer</button>
                    </span>
                  </div>
                {:else}
                  <div class="pub-page-row"><span class="pub-url muted">Aucun compte — publication sur le profil connecté, sans vérification d'identité.</span></div>
                {/each}

                {#if accountFormFor === p.id}
                  <div class="account-form">
                    <select bind:value={accountForm.platform}>
                      {#each PLATFORMS as pf}<option value={pf}>{pf}</option>{/each}
                    </select>
                    <select bind:value={accountForm.kind}>
                      {#each Object.entries(KIND_LABELS) as [k, label]}<option value={k}>{label}</option>{/each}
                    </select>
                    <input bind:value={accountForm.identity_name} placeholder="Nom exact affiché (ex: Noisyless)" />
                    <input bind:value={accountForm.page_url} placeholder="URL page (ex: https://www.linkedin.com/company/noisyless/admin/)" />
                    <input bind:value={accountForm.asset_id} placeholder="Asset ID Meta Business Suite (optionnel)" />
                    <div class="account-form-actions">
                      <button class="btn btn-secondary btn-sm" on:click={() => accountFormFor = null}>Annuler</button>
                      <button class="btn btn-primary btn-sm" on:click={() => saveAccount(p.id)} disabled={accountSaving}>
                        {accountSaving ? '…' : 'Ajouter'}
                      </button>
                    </div>
                  </div>
                {/if}
              </div>
              <div class="meta">Créé le {new Date(p.created_at).toLocaleDateString('fr-FR')}</div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</main>

<!-- Formulaire modal -->
{#if showForm}
  <div class="modal-backdrop" role="presentation">
    <div class="modal large" role="dialog" aria-modal="true">
      <div class="modal-head">
        <h2>{editingId ? 'Modifier le persona' : 'Nouveau persona'}</h2>
        <button class="modal-close" on:click={() => showForm = false}>×</button>
      </div>

      {#if formError}<div class="error-banner">{formError}</div>{/if}

      <div class="form-grid">
        <label class="form-field span-2">
          <span>Business Unit</span>
          <div class="bu-select">
            {#each BUS as bu}
              <button
                class="bu-btn bu-{bu}"
                class:selected={form.bu === bu}
                on:click={() => form.bu = bu}
                type="button"
              >{BU_LABELS[bu]}</button>
            {/each}
          </div>
        </label>

        <label class="form-field span-2">
          <span>Nom du persona</span>
          <input bind:value={form.nom} placeholder="Ex: Marie — Propriétaire location courte durée" />
        </label>

        <label class="form-field">
          <span>Cible (qui est-ce ?)</span>
          <textarea bind:value={form.cible} rows="3" placeholder="Propriétaires français de 1 à 5 biens Airbnb, 35-55 ans…"></textarea>
        </label>

        <label class="form-field">
          <span>Besoins</span>
          <textarea bind:value={form.besoins} rows="3" placeholder="Maintenir une note 4.8+, éviter les plaintes…"></textarea>
        </label>

        <label class="form-field span-2">
          <span>Frustrations</span>
          <textarea bind:value={form.frustrations} rows="3" placeholder="Plaintes de voisins, remboursements, avis négatifs…"></textarea>
        </label>

        <label class="form-field">
          <span>Ton éditorial</span>
          <input bind:value={form.ton} placeholder="Chaleureux mais expert, jamais vendeur" />
        </label>

        <label class="form-field">
          <span>Longueur cible (caractères)</span>
          <input type="number" bind:value={form.longueur_cible} min="100" max="5000" />
        </label>

        <label class="form-field">
          <span>Mots interdits <small>(séparés par des virgules)</small></span>
          <input bind:value={form.mots_interdits} placeholder="cheap, disruptif, révolutionnaire" />
        </label>

        <label class="form-field">
          <span>Emojis autorisés <small>(séparés par des espaces)</small></span>
          <input bind:value={form.emojis} placeholder="✅ 🔧 📊" />
        </label>

        <div class="form-field span-2 section-sep">
          <span class="section-label">Comptes de publication</span>
          <p class="section-hint">Les pages entreprise et comptes pro se gèrent dans la carte du persona (section « Comptes de publication »).</p>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" on:click={() => showForm = false}>Annuler</button>
        <button class="btn btn-primary" on:click={save} disabled={saving}>
          {saving ? 'Enregistrement…' : editingId ? 'Modifier' : 'Créer'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .page-header { display: flex; align-items: flex-start; justify-content: space-between; }

  .persona-list { display: flex; flex-direction: column; gap: 10px; }

  .persona-card {
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    overflow: hidden;
    transition: box-shadow 0.15s;
  }
  .persona-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }

  .persona-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px;
    cursor: pointer;
    user-select: none;
  }
  .persona-title { display: flex; align-items: center; gap: 12px; }
  .persona-nom { font-weight: 600; font-size: 15px; }

  .persona-actions { display: flex; align-items: center; gap: 8px; }
  .chevron { font-size: 18px; color: #9CA3AF; transition: transform 0.2s; }
  .chevron.rotated { transform: rotate(180deg); }

  .persona-body {
    border-top: 1px solid #F3F4F6;
    padding: 16px;
    animation: slideDown 0.15s ease;
  }
  @keyframes slideDown { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .field-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #9CA3AF; margin-bottom: 4px; }
  .field-value { font-size: 13px; color: #374151; line-height: 1.5; }

  .charte { display: flex; flex-direction: column; gap: 6px; }
  .charte-row { display: flex; gap: 8px; align-items: flex-start; font-size: 13px; }
  .charte-key { font-weight: 600; color: #6B7280; min-width: 100px; flex-shrink: 0; }
  .tags-row { display: flex; flex-wrap: wrap; gap: 4px; }
  .tag-bad { background: #FEE2E2; color: #B91C1C; padding: 1px 7px; border-radius: 4px; font-size: 11px; }
  .meta { font-size: 11px; color: #D1D5DB; margin-top: 8px; }

  /* Pages de publication */
  .pub-pages { margin-top: 14px; display: flex; flex-direction: column; gap: 6px; }
  .pub-page-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
  .pub-platform {
    width: 22px; height: 22px; border-radius: 4px; display: flex;
    align-items: center; justify-content: center; font-size: 9px;
    font-weight: 800; color: #fff; flex-shrink: 0; text-transform: uppercase;
  }
  .pub-platform.linkedin { background: #0077B5; }
  .pub-platform.instagram { background: linear-gradient(135deg, #f09433, #dc2743, #bc1888); }
  .pub-platform.facebook { background: #1877F2; }
  .pub-platform.tiktok { background: #111; }
  .pub-url { color: #6C63FF; text-decoration: none; font-weight: 500; }
  .pub-url:hover { text-decoration: underline; }
  .pub-url.muted { color: #9CA3AF; font-style: italic; }
  .pub-section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  .pub-page-row.disabled { opacity: 0.45; }
  .pub-kind { font-size: 11px; color: #6B7280; background: #F3F4F6; padding: 1px 7px; border-radius: 4px; flex-shrink: 0; }
  .pub-identity { font-weight: 600; color: #374151; flex-shrink: 0; }
  .pub-row-actions { margin-left: auto; display: flex; gap: 10px; }
  .link-btn { background: none; border: none; color: #6C63FF; font-size: 11px; cursor: pointer; padding: 0; }
  .link-btn.danger { color: #B91C1C; }
  .link-btn:hover { text-decoration: underline; }
  .account-form {
    margin-top: 8px; padding: 10px; border: 1px dashed #D1D5DB; border-radius: 8px;
    display: flex; flex-direction: column; gap: 6px;
  }
  .account-form input, .account-form select {
    border: 1px solid #D1D5DB; border-radius: 6px; padding: 6px 8px; font-size: 12px; font-family: inherit;
  }
  .account-form-actions { display: flex; justify-content: flex-end; gap: 8px; }

  /* Form section separator */
  .section-sep { margin-top: 4px; }
  .section-label { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #6C63FF; }
  .section-hint { font-size: 11px; color: #9CA3AF; font-weight: 400; margin-top: 3px; }
  .platform-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 16px; height: 16px; border-radius: 3px; font-size: 8px;
    font-weight: 800; color: #fff; vertical-align: middle; margin-left: 3px;
  }
  .platform-badge.li { background: #0077B5; }
  .platform-badge.ig { background: linear-gradient(135deg, #f09433, #dc2743, #bc1888); }

  .bu-tag {
    padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 700; text-transform: uppercase;
  }
  .bu-noisyless { background: #EDE9FE; color: #5B21B6; }
  .bu-afluxo    { background: #DCFCE7; color: #15803D; }
  .bu-mbhrep    { background: #FEF3C7; color: #92400E; }

  /* Form */
  .modal-backdrop {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.45);
    display: flex; align-items: center; justify-content: center;
    z-index: 200; padding: 16px;
  }
  .modal {
    background: #fff;
    border-radius: 12px;
    width: 100%;
    max-width: 680px;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 20px 60px rgba(0,0,0,0.25);
  }
  .modal.large { max-width: 780px; }
  .modal-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 20px 24px 16px;
    border-bottom: 1px solid #F3F4F6;
    position: sticky; top: 0; background: #fff; z-index: 1;
  }
  .modal-head h2 { font-size: 18px; font-weight: 700; margin: 0; }
  .modal-close {
    font-size: 22px; background: none; border: none;
    color: #9CA3AF; cursor: pointer; padding: 4px 8px;
  }
  .modal-close:hover { color: #111; }

  .form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 20px 24px;
  }
  .form-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 13px;
    font-weight: 500;
    color: #374151;
  }
  .form-field.span-2 { grid-column: 1 / -1; }
  .form-field input, .form-field textarea {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 13px;
    font-family: inherit;
    resize: vertical;
    transition: border-color 0.15s;
  }
  .form-field input:focus, .form-field textarea:focus {
    outline: none;
    border-color: #6C63FF;
    box-shadow: 0 0 0 3px rgba(108,99,255,0.1);
  }
  .form-field small { font-weight: 400; color: #9CA3AF; }

  .bu-select { display: flex; gap: 8px; }
  .bu-btn {
    padding: 6px 16px;
    border-radius: 6px;
    border: 2px solid #E5E7EB;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    background: #F9FAFB;
    color: #6B7280;
    transition: all 0.12s;
  }
  .bu-btn.selected.bu-noisyless { background: #EDE9FE; color: #5B21B6; border-color: #6C63FF; }
  .bu-btn.selected.bu-afluxo    { background: #DCFCE7; color: #15803D; border-color: #10B981; }
  .bu-btn.selected.bu-mbhrep    { background: #FEF3C7; color: #92400E; border-color: #F59E0B; }

  .modal-footer {
    display: flex; justify-content: flex-end; gap: 10px;
    padding: 16px 24px;
    border-top: 1px solid #F3F4F6;
    position: sticky; bottom: 0; background: #fff;
  }
</style>
