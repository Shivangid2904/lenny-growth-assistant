import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Artifact } from '../types/api';

interface ArtifactViewerProps {
  artifact: Artifact | null;
  onClose?: () => void;
}

export function ArtifactViewer({ artifact, onClose }: ArtifactViewerProps) {
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');
  const [copied, setCopied] = useState(false);

  if (!artifact) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-gray-50 border-l border-gray-200 p-8 text-center text-gray-500">
        <svg
          className="w-12 h-12 text-gray-300 mb-3"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="font-medium text-gray-600">No active artifact selected</p>
        <p className="text-xs text-gray-400 mt-1">
          Generate an artifact or select one from the chat to inspect it here.
        </p>
      </div>
    );
  }

  const handleCopy = () => {
    const textToCopy = artifact.content;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Build the complete srcDoc for HTML preview
  const buildSrcDoc = () => {
    const raw = artifact.content;
    const isFullDoc = /<!doctype\s+html|<html/i.test(raw);
    const extraCss = artifact.css ? `<style>${artifact.css}</style>` : '';

    if (isFullDoc) {
      if (extraCss) {
        return raw.replace(/<\/head>/i, `${extraCss}</head>`);
      }
      return raw;
    }

    return `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      body {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        margin: 0;
        padding: 1.5rem;
        color: #0f172a;
        background-color: #ffffff;
        line-height: 1.6;
      }
      * { box-sizing: border-box; }
    </style>
    ${extraCss}
  </head>
  <body>
    ${raw}
  </body>
</html>`;
  };

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center space-x-2 min-w-0">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
              artifact.type === 'html'
                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                : 'bg-blue-100 text-blue-800 border border-blue-200'
            }`}
          >
            {artifact.type.toUpperCase()}
          </span>
          <h2
            className="text-sm font-semibold text-gray-900 truncate max-w-[240px]"
            title={artifact.title}
          >
            {artifact.title}
          </h2>
        </div>

        <div className="flex items-center space-x-2">
          {artifact.type === 'html' && (
            <div className="flex rounded-md shadow-sm border border-gray-200 bg-white p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setViewMode('preview')}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  viewMode === 'preview'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Preview
              </button>
              <button
                type="button"
                onClick={() => setViewMode('code')}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  viewMode === 'code'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Code
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={handleCopy}
            title="Copy content"
            className="px-2.5 py-1 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded hover:bg-gray-50 hover:text-gray-900 transition-colors"
          >
            {copied ? 'Copied!' : 'Copy'}
          </button>

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              title="Close artifact viewer"
              className="text-gray-400 hover:text-gray-600 p-1 rounded-md hover:bg-gray-100"
              aria-label="Close"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-auto bg-gray-100 p-3">
        {artifact.type === 'html' ? (
          viewMode === 'preview' ? (
            <div className="w-full h-full bg-white rounded-lg shadow-sm overflow-hidden border border-gray-200 flex flex-col">
              {/*
                CRITICAL SECURITY BOUNDARY:
                - sandbox="allow-same-origin" isolates untrusted generated HTML.
                - NEVER include "allow-scripts" to prevent execution of malicious <script> tags or event handlers.
              */}
              <iframe
                data-testid="artifact-iframe"
                title={artifact.title}
                sandbox="allow-same-origin"
                srcDoc={buildSrcDoc()}
                className="w-full h-full border-0"
              />
            </div>
          ) : (
            <div className="h-full bg-gray-900 text-gray-100 p-4 rounded-lg overflow-auto font-mono text-xs">
              <pre className="whitespace-pre-wrap">{artifact.content}</pre>
            </div>
          )
        ) : (
          <div className="h-full bg-white rounded-lg shadow-sm border border-gray-200 p-6 overflow-auto">
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ node, ...props }) => (
                    <a {...props} target="_blank" rel="noopener noreferrer" />
                  ),
                }}
              >
                {artifact.content}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
