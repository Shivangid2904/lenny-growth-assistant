import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatComposer } from '../ChatComposer';

describe('ChatComposer', () => {
  it('renders correctly', () => {
    const mockOnSendMessage = vi.fn();
    render(<ChatComposer onSendMessage={mockOnSendMessage} disabled={false} />);
    
    const textarea = screen.getByPlaceholderText('Ask about product management, growth, or startup advice...');
    expect(textarea).toBeInTheDocument();
    expect(screen.getByText('Send')).toBeInTheDocument();
  });

  it('sends message on form submit', () => {
    const mockOnSendMessage = vi.fn();
    render(<ChatComposer onSendMessage={mockOnSendMessage} disabled={false} />);
    
    const textarea = screen.getByPlaceholderText('Ask about product management, growth, or startup advice...');
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    
    const sendButton = screen.getByText('Send');
    fireEvent.click(sendButton);
    
    expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
  });

  it('sends message on Enter key', () => {
    const mockOnSendMessage = vi.fn();
    render(<ChatComposer onSendMessage={mockOnSendMessage} disabled={false} />);
    
    const textarea = screen.getByPlaceholderText('Ask about product management, growth, or startup advice...');
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
    
    expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
  });

  it('does not send message on Shift+Enter', () => {
    const mockOnSendMessage = vi.fn();
    render(<ChatComposer onSendMessage={mockOnSendMessage} disabled={false} />);
    
    const textarea = screen.getByPlaceholderText('Ask about product management, growth, or startup advice...');
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', shiftKey: true });
    
    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  it('disables input when disabled', () => {
    const mockOnSendMessage = vi.fn();
    render(<ChatComposer onSendMessage={mockOnSendMessage} disabled={true} />);
    
    const textarea = screen.getByPlaceholderText('Ask about product management, growth, or startup advice...');
    const sendButton = screen.getByText('Sending...');
    
    expect(textarea).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  it('does not send empty messages', () => {
    const mockOnSendMessage = vi.fn();
    render(<ChatComposer onSendMessage={mockOnSendMessage} disabled={false} />);
    
    const sendButton = screen.getByText('Send');
    fireEvent.click(sendButton);
    
    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });
});
