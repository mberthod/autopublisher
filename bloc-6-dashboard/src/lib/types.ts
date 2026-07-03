export type Platform = 'linkedin' | 'instagram';
export type PostFormat = 'text_only' | 'image' | 'carousel';
export type PostStatus = 'draft' | 'validated' | 'scheduled' | 'published' | 'failed';
export type BU = 'noisyless' | 'afluxo' | 'mbhrep';

export interface Persona {
  id: string;
  bu: BU;
  nom: string;
  besoins: string;
  frustrations: string;
  cible: string;
  charte_branding: Record<string, unknown>;
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
  created_at: string;
  updated_at: string;
}

export type PersonaMap = Record<string, Persona>;
