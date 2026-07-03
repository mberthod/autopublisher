<script lang="ts">
  import type { PostStatus } from '$lib/types';
  export let status: PostStatus;

  const labels: Record<PostStatus, string> = {
    draft: 'Brouillon',
    validated: 'Validé',
    scheduled: 'Planifié',
    published: 'Publié',
    failed: 'Échec',
  };
</script>

<span class="badge badge-{status}">{labels[status] ?? status}</span>

<style>
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
    text-transform: uppercase;
  }
  .badge-draft     { background: #F3F4F6; color: #6B7280; }
  .badge-validated { background: #FEF3C7; color: #92400E; }
  .badge-scheduled { background: #DBEAFE; color: #1D4ED8; }
  .badge-published { background: #D1FAE5; color: #065F46; }
  .badge-failed    { background: #FEE2E2; color: #B91C1C; }
</style>
