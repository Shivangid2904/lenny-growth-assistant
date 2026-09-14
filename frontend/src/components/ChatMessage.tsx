import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message, Artifact } from '../types/api';

interface ChatMessageProps {
  message: Message;
  onOpenArtifact?: (artifact: Artifact) => void;
}

export function ChatMessage({ message, onOpenArtifact }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const citations = message.metadata?.citations || [];
  const isRefusal = message.content.includes("couldn't find enough relevant material");
  const artifact = message.metadata?.artifact;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg p-4 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        {!isUser && (
          <div className="font-semibold text-sm text-gray-600 mb-2">
            Lenny Growth Assistant
          </div>
        )}
        
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ node, ...props }) => (
                <a {...props} target="_blank" rel="noopener noreferrer" />
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Artifact Banner Card */}
        {artifact && (
          <div className="mt-3 p-3 bg-white rounded-lg border border-gray-200 shadow-sm flex items-center justify-between">
            <div className="flex items-center space-x-2.5 min-w-0 pr-2">
              <div className="p-2 bg-blue-50 text-blue-600 rounded-md">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-xs font-semibold text-gray-900 truncate">
                  {artifact.title}
                </div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">
                  {artifact.type} Artifact
                </div>
              </div>
            </div>
            {onOpenArtifact && (
              <button
                type="button"
                onClick={() => onOpenArtifact(artifact)}
                className="shrink-0 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded transition-colors"
              >
                View Artifact
              </button>
            )}
          </div>
        )}

        {!isUser && isRefusal && (
          <div className="mt-2 text-xs text-gray-500 italic">
            No matching source material found
          </div>
        )}

        {!isUser && citations.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="text-xs font-semibold text-gray-600 mb-2">
              Sources:
            </div>
            <div className="space-y-2">
              {citations.map((citation, index) => (
                <div
                  key={index}
                  className="text-xs bg-white p-2 rounded border border-gray-200"
                >
                  <div className="font-medium text-gray-700">
                    {citation.episode_title}
                  </div>
                  <div className="text-gray-600">
                    Guest: {citation.guest_name}
                  </div>
                  {citation.source_url && (
                    <a
                      href={citation.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      Listen to episode
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
