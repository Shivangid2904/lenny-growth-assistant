import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useChat } from '../useChat';
import * as api from '../../lib/api';

// Mock the API module
vi.mock('../../lib/api');

describe('useChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with empty messages', () => {
    const { result } = renderHook(() => useChat('session-123'));
    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('sends message and adds user message immediately', async () => {
    const mockSendMessage = vi.fn().mockImplementation(async () => {
      // Simulate immediate completion
      return Promise.resolve();
    });

    vi.mocked(api.sendMessage).mockImplementation(mockSendMessage);

    const { result } = renderHook(() => useChat('session-123'));

    await act(async () => {
      await result.current.sendMessage('Test message');
    });

    expect(result.current.messages).toHaveLength(2); // user + assistant placeholder
    expect(result.current.messages[0].role).toBe('user');
    expect(result.current.messages[0].content).toBe('Test message');
  });

  it('prevents duplicate submissions while loading', async () => {
    const mockSendMessage = vi.fn().mockImplementation(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    vi.mocked(api.sendMessage).mockImplementation(mockSendMessage);

    const { result } = renderHook(() => useChat('session-123'));

    // Start first message
    const firstPromise = act(async () => {
      await result.current.sendMessage('First message');
    });

    // Try to send second message immediately
    const secondPromise = act(async () => {
      await result.current.sendMessage('Second message');
    });

    await Promise.all([firstPromise, secondPromise]);

    expect(result.current.messages).toHaveLength(2); // Only first user + assistant
    expect(result.current.messages[0].content).toBe('First message');
  });

  it('handles token events and updates assistant message', async () => {
    const mockSendMessage = vi.fn().mockImplementation(async (
      _sessionId: string,
      _content: string,
      onToken: (delta: string) => void,
      onDone: (messageId: string, citations: any[], skill?: string, contentType?: string) => void,
      _onError: (code: string, message: string) => void
    ) => {
      // Simulate token stream
      onToken('Hello ');
      onToken('world!');
      
      // Simulate completion
      onDone('msg-123', [], 'chat', undefined);
    });

    vi.mocked(api.sendMessage).mockImplementation(mockSendMessage);

    const { result } = renderHook(() => useChat('session-123'));

    await act(async () => {
      await result.current.sendMessage('Test message');
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].role).toBe('assistant');
    expect(result.current.messages[1].content).toBe('Hello world!');
  });

  it('handles error events', async () => {
    const mockSendMessage = vi.fn().mockImplementation(async (
      _sessionId: string,
      _content: string,
      _onToken: (delta: string) => void,
      _onDone: (messageId: string, citations: any[], skill?: string, contentType?: string) => void,
      onError: (code: string, message: string) => void
    ) => {
      onError('MODEL_ERROR', 'Model failed to generate');
    });

    vi.mocked(api.sendMessage).mockImplementation(mockSendMessage);

    const { result } = renderHook(() => useChat('session-123'));

    await act(async () => {
      await result.current.sendMessage('Test message');
    });

    expect(result.current.error).toBe('MODEL_ERROR: Model failed to generate');
    expect(result.current.messages).toHaveLength(1); // Only user message
  });

  it('clears error when clearError is called', async () => {
    const mockSendMessage = vi.fn().mockImplementation(async (
      _sessionId: string,
      _content: string,
      _onToken: (delta: string) => void,
      _onDone: (messageId: string, citations: any[], skill?: string, contentType?: string) => void,
      onError: (code: string, message: string) => void
    ) => {
      onError('MODEL_ERROR', 'Model failed to generate');
    });

    vi.mocked(api.sendMessage).mockImplementation(mockSendMessage);

    const { result } = renderHook(() => useChat('session-123'));

    await act(async () => {
      await result.current.sendMessage('Test message');
    });

    expect(result.current.error).toBe('MODEL_ERROR: Model failed to generate');

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBe(null);
  });
});
