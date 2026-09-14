import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});

// Mock crypto.randomUUID for tests
if (!crypto.randomUUID) {
  Object.defineProperty(crypto, 'randomUUID', {
    value: () => 'test-uuid-' + Math.random().toString(36).substr(2, 9),
  });
}
