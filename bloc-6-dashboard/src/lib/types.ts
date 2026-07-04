export type Platform = 'linkedin' | 'instagram' | 'facebook' | 'tiktok';
export type PostFormat = 'text_only' | 'image' | 'carousel';
export type PostStatus = 'draft' | 'validated' | 'scheduled' | 'published' | 'failed';
export type BU = 'noisyless' | 'afluxo' | 'mbhrep';
export type AccountKind = 'personal' | 'company_page' | 'business_account';

export interface Account {
  id: string;
  persona_id: string;
  platform: Platform;
  kind: AccountKind;
  page_url: string | null;
  identity_name: string | null;
  asset_id: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Persona {
  id: string;
  bu: BU;
  nom: string;
  besoins: string;
  frustrations: string;
  cible: string;
  charte_branding: Record<string, unknown>;
  linkedin_page_url?: string;
  instagram_page_url?: string;
  created_at: string;
  updated_at: string;
}

export interface Planning {
  id: string;
  persona_id: string;
  date_debut: string;
  date_fin: string;
  created_at: string;
  updated_at: string;
}

export interface Post {
  id: string;
  planning_id: string;
  persona_id: string;
  platform: Platform;
  angle_editorial: string;
  format: PostFormat;
  text: string | null;
  image_url: string | null;
  carousel_urls: string[] | null;
  status: PostStatus;
  scheduled_for: string | null;
  published_at: string | null;
  published_url: string | null;
  error_code: string | null;
  error_message: string | null;
  account_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Positioning {
  id: string;
  bu: BU;
  content: string | null;
  keywords: string | null;
  updated_at: string;
}

export interface SessionStatus {
  id: string;
  platform: Platform;
  user_agent: string | null;
  valid: boolean;
  last_error: string | null;
  cookie_count: number;
  updated_at: string;
}

export type PersonaMap = Record<string, Persona>;

export const ERROR_LABELS: Record<string, string> = {
  WRONG_IDENTITY: "Mauvaise identité de publication — le post n'a PAS été publié",
  PUBLISH_UNCONFIRMED: "Publication non confirmée — vérifier manuellement",
  AUTH_REQUIRED: "Session déconnectée — se reconnecter dans le navigateur",
  SELECTOR_NOT_FOUND: "Élément introuvable dans la page (sélecteurs à mettre à jour)",
  UNKNOWN: "Erreur inconnue",
};

export function errorLabel(code: string | null | undefined): string {
  if (!code) return 'Échec';
  return ERROR_LABELS[code] ?? code;
}
