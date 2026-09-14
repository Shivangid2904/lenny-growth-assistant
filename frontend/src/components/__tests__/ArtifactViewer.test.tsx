import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ArtifactViewer } from '../ArtifactViewer';
import { Artifact } from '../../types/api';

describe('ArtifactViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock navigator.clipboard.writeText
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockImplementation(() => Promise.resolve()),
      },
    });
  });

  it('renders empty state when artifact is null', () => {
    render(<ArtifactViewer artifact={null} />);
    expect(screen.getByText('No active artifact selected')).toBeInTheDocument();
  });

  it('renders markdown artifact correctly', () => {
    const markdownArtifact: Artifact = {
      id: 'art-md-1',
      title: 'Retention Strategy Guide',
      type: 'markdown',
      content: '# Key Retention Strategies\n\n- Build habits\n- Drive activation',
    };

    render(<ArtifactViewer artifact={markdownArtifact} />);
    expect(screen.getByText('Retention Strategy Guide')).toBeInTheDocument();
    expect(screen.getByText('MARKDOWN')).toBeInTheDocument();
    expect(screen.getByText('Key Retention Strategies')).toBeInTheDocument();
    expect(screen.getByText('Build habits')).toBeInTheDocument();
  });

  it('renders HTML artifact with sandboxed iframe', () => {
    const htmlArtifact: Artifact = {
      id: 'art-html-1',
      title: 'Four Fits Dashboard',
      type: 'html',
      content: '<div class="dashboard"><h1>Four Fits</h1></div>',
      css: '.dashboard { padding: 20px; }',
    };

    render(<ArtifactViewer artifact={htmlArtifact} />);
    expect(screen.getByText('Four Fits Dashboard')).toBeInTheDocument();
    expect(screen.getByText('HTML')).toBeInTheDocument();

    const iframe = screen.getByTestId('artifact-iframe');
    expect(iframe).toBeInTheDocument();

    // CRITICAL SECURITY ASSERTIONS:
    // 1. iframe MUST have sandbox attribute
    expect(iframe.hasAttribute('sandbox')).toBe(true);

    const sandboxValue = iframe.getAttribute('sandbox') || '';
    // 2. sandbox MUST contain allow-same-origin
    expect(sandboxValue).toContain('allow-same-origin');
    // 3. sandbox MUST NEVER contain allow-scripts
    expect(sandboxValue).not.toContain('allow-scripts');

    // Verify srcdoc contains the HTML content
    const srcDoc = iframe.getAttribute('srcdoc') || '';
    expect(srcDoc).toContain('Four Fits');
  });

  it('toggles between preview and code view for HTML artifacts', () => {
    const htmlArtifact: Artifact = {
      id: 'art-html-2',
      title: 'Growth Loop Diagram',
      type: 'html',
      content: '<div class="loop">Loop Content</div>',
    };

    render(<ArtifactViewer artifact={htmlArtifact} />);
    expect(screen.getByTestId('artifact-iframe')).toBeInTheDocument();

    // Switch to code view
    const codeBtn = screen.getByRole('button', { name: /code/i });
    fireEvent.click(codeBtn);

    expect(screen.queryByTestId('artifact-iframe')).not.toBeInTheDocument();
    expect(screen.getByText('<div class="loop">Loop Content</div>')).toBeInTheDocument();

    // Switch back to preview
    const previewBtn = screen.getByRole('button', { name: /preview/i });
    fireEvent.click(previewBtn);
    expect(screen.getByTestId('artifact-iframe')).toBeInTheDocument();
  });

  it('calls onClose callback when close button is clicked', () => {
    const onClose = vi.fn();
    const artifact: Artifact = {
      id: 'art-1',
      title: 'Test Artifact',
      type: 'markdown',
      content: 'Some content',
    };

    render(<ArtifactViewer artifact={artifact} onClose={onClose} />);
    const closeBtn = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('copies artifact content to clipboard', async () => {
    const artifact: Artifact = {
      id: 'art-1',
      title: 'Copyable Artifact',
      type: 'markdown',
      content: 'Important playbook content',
    };

    render(<ArtifactViewer artifact={artifact} />);
    const copyBtn = screen.getByRole('button', { name: /copy/i });
    fireEvent.click(copyBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Important playbook content');
  });

  // =========================================================================
  // CRITICAL SECURITY TESTS: Malicious HTML / Script Execution Isolation
  // =========================================================================
  describe('Security isolation against malicious scripts', () => {
    it('isolates <script>document.body.innerHTML="PWNED"</script> inside sandboxed iframe without allow-scripts', () => {
      const maliciousPayload = '<script>document.body.innerHTML="PWNED"</script><h1>Safe Title</h1>';
      const maliciousArtifact: Artifact = {
        id: 'malicious-1',
        title: 'Untrusted Content',
        type: 'html',
        content: maliciousPayload,
      };

      const { container } = render(<ArtifactViewer artifact={maliciousArtifact} />);

      // Parent DOM must NOT be modified
      expect(document.body.innerHTML).not.toBe('PWNED');
      expect(container).toBeInTheDocument();

      const iframe = screen.getByTestId('artifact-iframe');
      const sandbox = iframe.getAttribute('sandbox') || '';
      expect(sandbox).toContain('allow-same-origin');
      expect(sandbox).not.toContain('allow-scripts');

      // The malicious script is confined to the iframe's srcdoc and cannot execute in parent
      const srcDoc = iframe.getAttribute('srcdoc') || '';
      expect(srcDoc).toContain('document.body.innerHTML="PWNED"');
    });

    it('isolates <img src=x onerror="document.body.innerHTML=\'PWNED\'"> without script execution permissions', () => {
      const maliciousPayload = '<img src="x" onerror="document.body.innerHTML=\'PWNED\'" />';
      const maliciousArtifact: Artifact = {
        id: 'malicious-2',
        title: 'Untrusted Image',
        type: 'html',
        content: maliciousPayload,
      };

      render(<ArtifactViewer artifact={maliciousArtifact} />);

      expect(document.body.innerHTML).not.toBe('PWNED');
      const iframe = screen.getByTestId('artifact-iframe');
      expect(iframe.getAttribute('sandbox')).toBe('allow-same-origin');
      expect(iframe.getAttribute('sandbox')).not.toContain('allow-scripts');
    });

    it('isolates <button onclick="document.body.innerHTML=\'PWNED\'">Click</button>', () => {
      const maliciousPayload = '<button onclick="document.body.innerHTML=\'PWNED\'">Click</button>';
      const maliciousArtifact: Artifact = {
        id: 'malicious-3',
        title: 'Untrusted Button',
        type: 'html',
        content: maliciousPayload,
      };

      render(<ArtifactViewer artifact={maliciousArtifact} />);

      expect(document.body.innerHTML).not.toBe('PWNED');
      const iframe = screen.getByTestId('artifact-iframe');
      expect(iframe.getAttribute('sandbox')).toBe('allow-same-origin');
      expect(iframe.getAttribute('sandbox')).not.toContain('allow-scripts');
    });
  });
});
