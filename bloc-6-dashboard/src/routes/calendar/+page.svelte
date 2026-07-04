<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { Post, Persona, PersonaMap } from '$lib/types';
  import PlatformIcon from '$lib/components/PlatformIcon.svelte';

  let posts: Post[] = [];
  let personaMap: PersonaMap = {};
  let loading = true;
  let error = '';
  let selectedPost: Post | null = null;
  let editing = false;
  let editDate = '';
  let editStatus = '';
  let saving = false;
  let deleting = false;
  let saveError = '';

  const BUS = ['noisyless', 'afluxo', 'mbhrep'] as const;
  const BU_LABELS: Record<string, string> = { noisyless: 'Noisyless', afluxo: 'Afluxo', mbhrep: 'MBHREP' };

  // 30-day window: 7 days ago → 23 days ahead
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - 7);
  const days: string[] = Array.from({ length: 30 }, (_, i) => {
    const d = new Date(startDate);
    d.setDate(d.getDate() + i);
    return d.toISOString().split('T')[0];
  });

  const todayStr = new Date().toISOString().split('T')[0];

  onMount(async () => {
    try {
      const [fetchedPosts, personas] = await Promise.all([
        api.posts.list({ limit: '500' }),
        api.personas.list(),
      ]);
      personaMap = Object.fromEntries(personas.map(p => [p.id, p]));
      posts = fetchedPosts;
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });

  function getPostsForCell(bu: string, day: string): Post[] {
    return posts.filter(p => {
      const persona = personaMap[p.persona_id];
      if (!persona || persona.bu !== bu) return false;
      if (!p.scheduled_for) return false;
      return p.scheduled_for.split('T')[0] === day;
    });
  }

  const statusColors: Record<string, string> = {
    draft: '#9CA3AF',
    validated: '#F59E0B',
    scheduled: '#3B82F6',
    published: '#10B981',
    failed: '#EF4444',
  };

  function formatDay(dayStr: string): string {
    const d = new Date(dayStr + 'T12:00:00');
    return d.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  function filterText(platform: string, format: string): string {
    const f: Record<string, string> = { text_only: '📝', image: '📷', carousel: '📸' };
    const pf: Record<string, string> = { linkedin: 'L', instagram: 'I' };
    return `${f[format] ?? '?'}${pf[platform] ?? '?'}`;
  }

  function openPost(p: Post) {
    selectedPost = p;
    editing = false;
    saveError = '';
    editDate = p.scheduled_for ? new Date(p.scheduled_for).toISOString().slice(0, 16) : '';
    editStatus = p.status;
  }

  async function saveEdit() {
    if (!selectedPost) return;
    saving = true;
    saveError = '';
    try {
      const updated = await api.posts.update(selectedPost.id, {
        scheduled_for: editDate ? new Date(editDate).toISOString() : undefined,
        status: editStatus as Post['status'],
      });
      posts = posts.map(p => p.id === updated.id ? updated : p);
      selectedPost = updated;
      editing = false;
    } catch (e) {
      saveError = e instanceof Error ? e.message : String(e);
    } finally {
      saving = false;
    }
  }

  async function deletePost() {
    if (!selectedPost) return;
    if (!confirm('Supprimer cette publication ? Cette action est irréversible.')) return;
    deleting = true;
    try {
      await api.posts.delete(selectedPost.id);
      posts = posts.filter(p => p.id !== selectedPost!.id);
      selectedPost = null;
    } catch (e) {
      saveError = e instanceof Error ? e.message : String(e);
      deleting = false;
    }
  }
</script>

<svelte:head><title>Calendar — SaaS RSE</title></svelte:head>

<main class="page">
  <div class="page-header">
    <h1>Calendar</h1>
    <p class="subtitle">Planning éditorial · 30 jours</p>
  </div>

  {#if loading}
    <div class="loading">Chargement…</div>
  {:else if error}
    <div class="error-banner">{error}</div>
  {:else}
    <div class="calendar-wrapper">
      <table class="calendar-table">
        <thead>
          <tr>
            <th class="bu-col">BU</th>
            {#each days as day}
              <th class:today={day === todayStr}>{formatDay(day)}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each BUS as bu}
            <tr>
              <td class="bu-cell bu-{bu}">{BU_LABELS[bu]}</td>
              {#each days as day}
                {@const cellPosts = getPostsForCell(bu, day)}
                <td class="day-cell" class:today={day === todayStr}>
                  {#each cellPosts as p}
                    <button
                      class="chip"
                      style="background: {statusColors[p.status]}22; border-color: {statusColors[p.status]}66; color: {statusColors[p.status]}"
                      on:click={() => openPost(p)}
                      title={p.text?.slice(0, 100) ?? p.angle_editorial}
                    >
                      {filterText(p.platform, p.format)}
                    </button>
                  {/each}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <div class="legend">
      <span>Légende :</span>
      <span>📝 Texte</span><span>📷 Image</span><span>📸 Carrousel</span>
      <span>L=LinkedIn</span><span>I=Instagram</span>
      <span class="dot" style="background:#9CA3AF"></span><span>Brouillon</span>
      <span class="dot" style="background:#F59E0B"></span><span>Validé</span>
      <span class="dot" style="background:#3B82F6"></span><span>Planifié</span>
      <span class="dot" style="background:#10B981"></span><span>Publié</span>
      <span class="dot" style="background:#EF4444"></span><span>Échec</span>
    </div>
  {/if}
</main>

<!-- Modal post detail -->
{#if selectedPost}
  {@const p = selectedPost}
  {@const persona = personaMap[p.persona_id]}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <div class="modal-backdrop" on:click={() => selectedPost = null} role="presentation">
    <div class="modal" on:click|stopPropagation role="dialog" aria-modal="true">
      <button class="modal-close" on:click={() => selectedPost = null}>×</button>
      <div class="modal-tags">
        {#if persona}<span class="bu-tag bu-{persona.bu}">{BU_LABELS[persona.bu]}</span>{/if}
        <PlatformIcon platform={p.platform} size={18} />
        <span class="format-small">{p.format}</span>
      </div>
      <p class="modal-text">{p.text ?? p.angle_editorial}</p>
      {#if p.scheduled_for}
        <p class="modal-date">Planifié : {new Date(p.scheduled_for).toLocaleString('fr-FR')}</p>
      {/if}
      {#if p.status === 'failed'}
        <p class="modal-error">⚠ {p.error_code}: {p.error_message}</p>
      {/if}
    </div>
  </div>
{/if}

<style>
  .calendar-wrapper {
    overflow-x: auto;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    background: #fff;
  }
  .calendar-table {
    border-collapse: collapse;
    min-width: 100%;
    font-size: 12px;
  }
  th, td {
    padding: 8px 10px;
    border: 1px solid #F3F4F6;
    text-align: center;
    white-space: nowrap;
  }
  th {
    background: #F9FAFB;
    font-weight: 600;
    color: #6B7280;
    font-size: 11px;
  }
  th.today { background: #EEF2FF; color: #6C63FF; }
  td.today { background: #F5F3FF; }
  .bu-col { width: 90px; font-weight: 700; }
  .bu-cell {
    font-weight: 600;
    font-size: 12px;
    text-align: left;
    padding-left: 12px;
  }
  .bu-noisyless { color: #5B21B6; background: #F5F3FF; }
  .bu-afluxo    { color: #15803D; background: #F0FDF4; }
  .bu-mbhrep    { color: #92400E; background: #FFFBEB; }
  .day-cell {
    min-width: 52px;
    vertical-align: middle;
    padding: 4px;
  }
  .chip {
    display: inline-block;
    padding: 2px 5px;
    border-radius: 4px;
    border: 1px solid;
    font-size: 11px;
    cursor: pointer;
    margin: 1px;
    background: none;
    font-family: inherit;
  }
  .chip:hover { opacity: 0.75; }
  .legend {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 14px;
    font-size: 12px;
    color: #6B7280;
    flex-wrap: wrap;
  }
  .dot {
    display: inline-block;
    width: 10px; height: 10px;
    border-radius: 50%;
  }

  /* Modal */
  .modal-backdrop {
    position: fixed; inset: 0;
    background: rgba(0,0,0,0.4);
    display: flex; align-items: center; justify-content: center;
    z-index: 200;
  }
  .modal {
    background: #fff;
    border-radius: 12px;
    padding: 24px;
    max-width: 520px;
    width: 90%;
    position: relative;
    box-shadow: 0 20px 60px rgba(0,0,0,0.2);
  }
  .modal-close {
    position: absolute; top: 12px; right: 16px;
    font-size: 22px; background: none; border: none;
    color: #9CA3AF; cursor: pointer; padding: 4px;
  }
  .modal-close:hover { color: #111; }
  .modal-tags { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
  .bu-tag {
    padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 700; text-transform: uppercase;
  }
  .bu-noisyless { background: #EDE9FE; color: #5B21B6; }
  .bu-afluxo    { background: #DCFCE7; color: #15803D; }
  .bu-mbhrep    { background: #FEF3C7; color: #92400E; }
  .format-small { font-size: 11px; color: #9CA3AF; }
  .modal-text {
    font-size: 14px; color: #374151;
    line-height: 1.6; margin: 0 0 12px;
  }
  .modal-date { font-size: 12px; color: #9CA3AF; margin: 0; }
  .modal-error {
    font-size: 12px; color: #B91C1C;
    background: #FEE2E2; padding: 8px; border-radius: 5px; margin-top: 8px;
  }

  .modal-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .status-pill {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
  }
  .status-draft     { background: #F3F4F6; color: #6B7280; }
  .status-validated { background: #FEF3C7; color: #92400E; }
  .status-scheduled { background: #DBEAFE; color: #1E40AF; }
  .status-published { background: #DCFCE7; color: #15803D; }
  .status-failed    { background: #FEE2E2; color: #B91C1C; }

  .edit-form {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 14px;
    background: #F9FAFB;
    border-radius: 8px;
    margin-bottom: 14px;
  }
  .edit-label {
    display: flex;
    flex-direction: column;
    gap: 5px;
    font-size: 12px;
    font-weight: 600;
    color: #6B7280;
  }
  .edit-input {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    font-family: inherit;
    background: #fff;
  }
  .edit-input:focus {
    outline: none;
    border-color: #6C63FF;
    box-shadow: 0 0 0 2px rgba(108,99,255,0.15);
  }

  .modal-actions {
    display: flex;
    gap: 8px;
    margin-top: 14px;
    border-top: 1px solid #F3F4F6;
    padding-top: 14px;
  }
  .btn-edit {
    padding: 7px 16px;
    background: #F5F3FF;
    border: 1px solid #DDD6FE;
    border-radius: 6px;
    color: #5B21B6;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }
  .btn-edit:hover { background: #EDE9FE; }
  .btn-save {
    padding: 7px 16px;
    background: #6C63FF;
    border: none;
    border-radius: 6px;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }
  .btn-save:disabled { opacity: 0.5; cursor: default; }
  .btn-save:not(:disabled):hover { background: #5A52E8; }
  .btn-cancel {
    padding: 7px 14px;
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    color: #6B7280;
    font-size: 13px;
    cursor: pointer;
  }
  .btn-cancel:hover { background: #F3F4F6; }
  .btn-delete {
    margin-left: auto;
    padding: 7px 14px;
    background: #FEF2F2;
    border: 1px solid #FECACA;
    border-radius: 6px;
    color: #B91C1C;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }
  .btn-delete:hover { background: #FEE2E2; }
  .btn-delete:disabled { opacity: 0.5; cursor: default; }

</style>
