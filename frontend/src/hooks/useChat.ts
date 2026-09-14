import { useState, useCallback, useRef } from 'react';
import { sendMessage as sendApiMessage, ApiError } from '../lib/api';
import { Message, Citation } from '../types/api';

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearError: () => void;
}

export function useChat(sessionId: string): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isStreamingRef = useRef(false);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (isLoading || isStreamingRef.current) {
      return;
    }

    setIsLoading(true);
    setError(null);
    isStreamingRef.current = true;

    // Add user message immediately
    const userMessage: Message = {
      id: crypto.randomUUID(),
      session_id: sessionId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Create placeholder for assistant message
    const assistantMessageId = crypto.randomUUID();
    const assistantMessage: Message = {
      id: assistantMessageId,
      session_id: sessionId,
      role: 'assistant',
      content: '',
      metadata: { citations: [] },
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, assistantMessage]);

    let accumulatedContent = '';
    let citations: Citation[] = [];
    let skill: string | undefined;
    let contentType: string | undefined;

    try {
      await sendApiMessage(
        sessionId,
        content,
        // onToken
        (delta: string) => {
          accumulatedContent += delta;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: accumulatedContent }
                : msg
            )
          );
        },
        // onDone
        (messageId: string, newCitations: Citation[], newSkill?: string, newContentType?: string) => {
          citations = newCitations;
          skill = newSkill;
          contentType = newContentType;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    id: messageId,
                    metadata: {
                      citations,
                      skill,
                      content_type: contentType,
                    },
                  }
                : msg
            )
          );
        },
        // onError
        (code: string, message: string) => {
          setError(`${code}: ${message}`);
          setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId));
        }
      );
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError('An unexpected error occurred');
      }
      setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId));
    } finally {
      setIsLoading(false);
      isStreamingRef.current = false;
    }
  }, [sessionId, isLoading]);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearError,
  };
}
