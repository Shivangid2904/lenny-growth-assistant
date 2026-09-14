import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatMessage } from '../ChatMessage';
import { Message } from '../../types/api';

describe('ChatMessage', () => {
  it('renders user message correctly', () => {
    const userMessage: Message = {
      id: '1',
      session_id: 'session-1',
      role: 'user',
      content: 'Hello, how are you?',
      created_at: '2024-01-01T00:00:00Z',
    };

    render(<ChatMessage message={userMessage} />);
    expect(screen.getByText('Hello, how are you?')).toBeInTheDocument();
  });

  it('renders assistant message correctly', () => {
    const assistantMessage: Message = {
      id: '2',
      session_id: 'session-1',
      role: 'assistant',
      content: 'I am doing well, thank you!',
      created_at: '2024-01-01T00:00:00Z',
    };

    render(<ChatMessage message={assistantMessage} />);
    expect(screen.getByText('I am doing well, thank you!')).toBeInTheDocument();
    expect(screen.getByText('Lenny Growth Assistant')).toBeInTheDocument();
  });

  it('renders markdown content', () => {
    const message: Message = {
      id: '3',
      session_id: 'session-1',
      role: 'assistant',
      content: '# Heading\n\nThis is **bold** text.',
      created_at: '2024-01-01T00:00:00Z',
    };

    render(<ChatMessage message={message} />);
    expect(screen.getByText('Heading')).toBeInTheDocument();
    expect(screen.getByText('bold')).toBeInTheDocument();
  });

  it('renders citations when present', () => {
    const message: Message = {
      id: '4',
      session_id: 'session-1',
      role: 'assistant',
      content: 'Here is some content.',
      metadata: {
        citations: [
          {
            episode_title: 'Test Episode',
            guest_name: 'Test Guest',
            source_url: 'https://example.com',
            chunk_index: 0,
          },
        ],
      },
      created_at: '2024-01-01T00:00:00Z',
    };

    render(<ChatMessage message={message} />);
    expect(screen.getByText('Sources:')).toBeInTheDocument();
    expect(screen.getByText('Test Episode')).toBeInTheDocument();
    expect(screen.getByText('Guest: Test Guest')).toBeInTheDocument();
    expect(screen.getByText('Listen to episode')).toBeInTheDocument();
  });

  it('shows "No matching source material" cue for grounded refusals', () => {
    const refusalMessage: Message = {
      id: '5',
      session_id: 'session-1',
      role: 'assistant',
      content: "I couldn't find enough relevant material in Lenny's Podcast transcripts to answer that reliably.",
      metadata: {
        citations: [],
      },
      created_at: '2024-01-01T00:00:00Z',
    };

    render(<ChatMessage message={refusalMessage} />);
    expect(screen.getByText('No matching source material found')).toBeInTheDocument();
  });

  it('does not show error styling for grounded refusals', () => {
    const refusalMessage: Message = {
      id: '6',
      session_id: 'session-1',
      role: 'assistant',
      content: "I couldn't find enough relevant material in Lenny's Podcast transcripts to answer that reliably.",
      metadata: {
        citations: [],
      },
      created_at: '2024-01-01T00:00:00Z',
    };

    const { container } = render(<ChatMessage message={refusalMessage} />);
    const messageBubble = container.querySelector('.bg-gray-100');
    expect(messageBubble).toBeInTheDocument();
    expect(messageBubble).not.toHaveClass('bg-red-50');
  });
});
