<script lang="ts">
  import { tick } from 'svelte';
  import { grillme } from '$lib/api';
  import type { GrilledMeSession, GrilledMeMessage } from "$lib/api";
  import type { BU } from "$lib/types";

  const BUS: BU[] = ['noisyless', 'afluxo', 'mbhrep'];
  const BU_LABELS: Record<BU, string> = { noisyless: 'Noisyless', afluxo: 'Afluxo', mbhrep: 'MBHREP' };

  type ChatMsg = { role: 'user' | 'assistant'; content: string };

  let phase: 'pick' | 'chat' | 'done' = 'pick';
  let selectedBu: BU = 'noisyless';
  let session: GrilledMeSession | null = null;
  let messages: ChatMsg[] = [];
  let userInput = '';
  let sending = false;
  let error = '';
  let generatedPersonaId: string | null = null;
  let loadingPersona = false;

  let chatEl: HTMLDivElement;

  async function startSession() {
    error = '';
    try {
      session = await grillme.startSession(selectedBu);
      // Premier message de l'assistant (la première question)
      messages = [{ role: 'assistant', content: session.first_question }];
      phase = 'chat';
      await scrollDown();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  async function send() {
    if (!userInput.trim() || sending || !session) return;
    const text = userInput.trim();
    userInput = '';
    messages = [...messages, { role: 'user', content: text }];
    sending = true;
    error = '';
    await scrollDown();

    try {
      const resp: GrilledMeMessage = await grillme.sendMessage(session.session_id, text);
      if (resp.is_complete) {
        // Récupère le persona généré
        loadingPersona = true;
        try {
          const result = await grillme.getPersona(session.session_id);
          generatedPersonaId = result.persona.id;
          messages = [...messages, {
            role: 'assistant',
            content: `Parfait ! J'ai créé le persona **${result.persona.nom}** pour **${BU_LABELS[result.persona.bu]}**.\n\nTu peux maintenant le retrouver dans la page Personas.`
          }];
        } catch {
          messages = [...messages, { role: 'assistant', content: resp.next_question ?? "" }];
        }
        loadingPersona = false;
        phase = 'done';
      } else {
        messages = [...messages, { role: 'assistant', content: resp.next_question ?? "" }];
      }
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
      userInput = text; // restore
    } finally {
      sending = false;
      await scrollDown();
    }
  }

  async function scrollDown() {
    await tick();
    chatEl?.scrollTo({ top: chatEl.scrollHeight, behavior: 'smooth' });
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function restart() {
    phase = 'pick';
    session = null;
    messages = [];
    userInput = '';
    generatedPersonaId = null;
    error = '';
  }
</script>

<svelte:head><title>GrilledMe — SaaS RSE</title></svelte:head>

<main class="page">
  <div class="page-header">
    <div>
      <h1 class="gm-title">GrilledMe <span class="badge-ai">IA</span></h1>
      <p class="subtitle">Génère un persona complet en conversant avec l'IA</p>
    </div>
    {#if phase !== 'pick'}
      <button class="btn btn-secondary" on:click={restart}>Nouvelle session</button>
    {/if}
  </div>

  {#if error}<div class="error-banner">{error}</div>{/if}

  {#if phase === 'pick'}
    <div class="pick-card">
      <div class="pick-icon">🔥</div>
      <h2>Pour quelle BU veux-tu créer un persona ?</h2>
      <div class="bu-select">
        {#each BUS as bu}
          <button
            class="bu-btn bu-{bu}"
            class:selected={selectedBu === bu}
            on:click={() => selectedBu = bu}
            type="button"
          >
            {BU_LABELS[bu]}
          </button>
        {/each}
      </div>
      <p class="pick-hint">L'IA va te poser une série de questions pour construire le profil de ta cible idéale et la charte éditoriale associée.</p>
      <button class="btn btn-primary btn-lg" on:click={startSession}>
        Commencer l'entretien →
      </button>
    </div>
  {:else}
    <div class="chat-wrapper">
      <div class="chat-box" bind:this={chatEl}>
        {#each messages as msg, i (i)}
          <div class="msg msg-{msg.role}">
            {#if msg.role === 'assistant'}
              <div class="avatar">🔥</div>
            {/if}
            <div class="bubble bubble-{msg.role}">
              <!-- eslint-disable-next-line svelte/no-at-html-tags -->
              {@html (msg.content ?? '').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')}
            </div>
            {#if msg.role === 'user'}
              <div class="avatar avatar-user">👤</div>
            {/if}
          </div>
        {/each}

        {#if sending || loadingPersona}
          <div class="msg msg-assistant">
            <div class="avatar">🔥</div>
            <div class="bubble bubble-assistant typing">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
          </div>
        {/if}
      </div>

      {#if phase === 'done'}
        <div class="done-bar">
          <span class="done-icon">✅</span>
          <span>Persona créé avec succès !</span>
          <a href="/personas" class="btn btn-primary btn-sm">Voir les personas</a>
          {#if generatedPersonaId}
            <a href="/personas?highlight={generatedPersonaId}" class="btn btn-secondary btn-sm">Voir ce persona</a>
          {/if}
        </div>
      {:else}
        <div class="input-bar">
          <textarea
            bind:value={userInput}
            on:keydown={handleKey}
            placeholder="Écris ta réponse… (Entrée pour envoyer, Shift+Entrée pour saut de ligne)"
            rows="2"
            disabled={sending}
          ></textarea>
          <button class="send-btn" on:click={send} disabled={sending || !userInput.trim()}>
            {#if sending}
              <span class="spinner-sm"></span>
            {:else}
              ↑
            {/if}
          </button>
        </div>
      {/if}
    </div>
  {/if}
</main>

<style>
  .gm-title { display: flex; align-items: center; gap: 10px; }
  .badge-ai {
    font-size: 11px; font-weight: 700;
    background: linear-gradient(135deg, #f97316, #ef4444);
    color: #fff;
    padding: 2px 7px;
    border-radius: 20px;
    vertical-align: middle;
  }

  /* --- PICK PHASE --- */
  .pick-card {
    max-width: 520px;
    margin: 40px auto;
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 16px;
    padding: 40px 36px;
    text-align: center;
    box-shadow: 0 4px 24px rgba(0,0,0,0.07);
  }
  .pick-icon { font-size: 48px; margin-bottom: 16px; }
  .pick-card h2 { font-size: 20px; font-weight: 700; margin-bottom: 24px; color: #111827; }
  .pick-hint { color: #6B7280; font-size: 13px; line-height: 1.6; margin: 20px 0 28px; }

  .bu-select { display: flex; gap: 10px; justify-content: center; }
  .bu-btn {
    padding: 8px 20px;
    border-radius: 8px;
    border: 2px solid #E5E7EB;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    background: #F9FAFB;
    color: #6B7280;
    transition: all 0.12s;
  }
  .bu-btn:hover { border-color: #D1D5DB; }
  .bu-btn.selected.bu-noisyless { background: #EDE9FE; color: #5B21B6; border-color: #6C63FF; }
  .bu-btn.selected.bu-afluxo    { background: #DCFCE7; color: #15803D; border-color: #10B981; }
  .bu-btn.selected.bu-mbhrep    { background: #FEF3C7; color: #92400E; border-color: #F59E0B; }

  .btn-lg { padding: 12px 32px; font-size: 15px; }

  /* --- CHAT --- */
  .chat-wrapper {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 200px);
    min-height: 420px;
    background: #fff;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    overflow: hidden;
  }

  .chat-box {
    flex: 1;
    overflow-y: auto;
    padding: 24px 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    scroll-behavior: smooth;
  }

  .msg {
    display: flex;
    align-items: flex-end;
    gap: 10px;
  }
  .msg-user { flex-direction: row-reverse; }

  .avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    background: #F3F4F6;
    flex-shrink: 0;
  }
  .avatar-user { background: #EDE9FE; }

  .bubble {
    max-width: 70%;
    padding: 12px 16px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.6;
  }
  .bubble-assistant {
    background: #F9FAFB;
    border: 1px solid #E5E7EB;
    border-bottom-left-radius: 4px;
    color: #111827;
  }
  .bubble-user {
    background: #6C63FF;
    color: #fff;
    border-bottom-right-radius: 4px;
  }

  /* Typing indicator */
  .typing {
    display: flex;
    gap: 4px;
    align-items: center;
    padding: 14px 16px;
  }
  .dot {
    width: 7px; height: 7px;
    background: #9CA3AF;
    border-radius: 50%;
    animation: bounce 1.2s infinite;
  }
  .dot:nth-child(2) { animation-delay: 0.2s; }
  .dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-6px); }
  }

  /* Input bar */
  .input-bar {
    display: flex;
    gap: 10px;
    align-items: flex-end;
    padding: 14px 16px;
    border-top: 1px solid #F3F4F6;
    background: #fff;
  }
  .input-bar textarea {
    flex: 1;
    border: 1px solid #D1D5DB;
    border-radius: 10px;
    padding: 10px 12px;
    font-family: inherit;
    font-size: 14px;
    resize: none;
    line-height: 1.5;
  }
  .input-bar textarea:focus {
    outline: none;
    border-color: #6C63FF;
    box-shadow: 0 0 0 3px rgba(108,99,255,0.1);
  }

  .send-btn {
    width: 40px; height: 40px;
    border-radius: 50%;
    background: #6C63FF;
    color: #fff;
    border: none;
    font-size: 18px;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    transition: background 0.15s;
  }
  .send-btn:disabled { background: #E5E7EB; color: #9CA3AF; cursor: default; }
  .send-btn:not(:disabled):hover { background: #5A52E8; }

  .spinner-sm {
    width: 16px; height: 16px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Done bar */
  .done-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 20px;
    border-top: 1px solid #F3F4F6;
    background: #F0FDF4;
    font-weight: 600;
    font-size: 14px;
    color: #15803D;
  }
  .done-icon { font-size: 18px; }
</style>
