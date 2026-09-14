export interface Citation {
  episode_id?: string;
  episode_title: string;
  guest_name: string;
  source_url: string;
  chunk_index: number;
  distance?: number;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: {
    citations?: Citation[];
    skill?: string;
    content_type?: string;
  };
  created_at: string;
}

export interface Session {
  id: string;
  title?: string;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail extends Session {
  messages: Message[];
}

export interface SSEEvent {
  event: 'token' | 'done' | 'error';
  data: SSEEventData;
}

export interface SSETokenData {
  delta: string;
}

export interface SSEDoneData {
  message_id: string;
  citations: Citation[];
  status: 'completed';
  skill?: string;
  content_type?: string;
}

export interface SSEErrorData {
  code: string;
  message: string;
}

export type SSEEventData = SSETokenData | SSEDoneData | SSEErrorData;
