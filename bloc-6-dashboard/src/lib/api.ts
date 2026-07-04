import { PUBLIC_API_URL } from '$env/static/public';
import type { Post, Persona, Planning } from './types';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${PUBLIC_API_URL}${path}`, options);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API ${path}: HTTP ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  posts: {
    list(params: Record<string, string | undefined> = {}): Promise<Post[]> {
      const qs = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined) qs.set(k, v);
      }
      const q = qs.toString() ? `?${qs}` : '';
      return request<Post[]>(`/posts${q}`);
    },
    update(id: string, data: Partial<Post>): Promise<Post> {
      return request<Post>(`/posts/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    },
    delete(id: string): Promise<void> {
      return request<void>(`/posts/${id}`, { method: 'DELETE' });
    },
  },
  personas: {
    list(): Promise<Persona[]> {
      return request<Persona[]>('/personas');
    },
    create(data: Partial<Persona>): Promise<Persona> {
      return request<Persona>('/personas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    },
    update(id: string, data: Partial<Persona>): Promise<Persona> {
      return request<Persona>(`/personas/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    },
    delete(id: string): Promise<void> {
      return request<void>(`/personas/${id}`, { method: 'DELETE' });
    },
  },
  plannings: {
    list(): Promise<Planning[]> {
      return request<Planning[]>('/plannings');
    },
    create(data: { persona_id: string; date_debut: string; date_fin: string }): Promise<Planning> {
      return request<Planning>('/plannings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    },
  },
  posts_create: {
    create(data: { planning_id: string; persona_id: string; platform: string; angle_editorial: string; format: string }): Promise<Post> {
      return request<Post>('/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
    },
  },
};


// ── GrilledMe (bloc-2, port 8001) ──────────────────────────────────────────
import { PUBLIC_GRILLME_URL } from '$env/static/public';

async function grillmeRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${PUBLIC_GRILLME_URL}${path}`, options);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`GrilledMe ${path}: HTTP ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export interface GrilledMeSession {
  session_id: string;
  first_question: string;
}

export interface GrilledMeMessage {
  next_question: string;
  is_complete: boolean;
  matrix_progress: number;
  current_field: string;
  persona?: import('./types').Persona;
}

export const grillme = {
  startSession(bu: string): Promise<GrilledMeSession> {
    return grillmeRequest<GrilledMeSession>('/grillme/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bu }),
    });
  },
  sendMessage(sessionId: string, userMessage: string): Promise<GrilledMeMessage> {
    return grillmeRequest<GrilledMeMessage>(`/grillme/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_message: userMessage }),
    });
  },
  getPersona(sessionId: string): Promise<{ persona: import('./types').Persona }> {
    return grillmeRequest(`/grillme/sessions/${sessionId}/persona`);
  },
};


// ── Generation (bloc-3, port 8003) ──────────────────────────────────────────
import { PUBLIC_GENERATION_URL } from '$env/static/public';

async function genRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${PUBLIC_GENERATION_URL}${path}`, options);
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Generation ${path}: HTTP ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export interface GenerateRequest {
  planning_id: string;
  persona_id: string;
  angle_editorial: string;
  format: 'text_only' | 'image' | 'carousel';
  platform: 'linkedin' | 'instagram';
}

export interface GenerateResponse {
  post_id: string;
  text: string;
  format: string;
  platform: string;
  image_url?: string;
  carousel_urls?: string[];
  visual_headline?: string;
  generation_metadata?: Record<string, unknown>;
}

export interface IdeaGenerateRequest {
  persona_id: string;
  keywords: string;
  platform: 'linkedin' | 'instagram' | 'both';
  n: number;
}

export interface EditorialIdea {
  angle: string;
  rationale: string;
  platform: string;
}

export interface IdeaGenerateResponse {
  ideas: EditorialIdea[];
}

export const generation = {
  generate(data: GenerateRequest): Promise<GenerateResponse> {
    return genRequest<GenerateResponse>('/api/v1/posts/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },
  generateIdeas(data: IdeaGenerateRequest): Promise<IdeaGenerateResponse> {
    return genRequest<IdeaGenerateResponse>('/api/v1/ideas/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },
};
