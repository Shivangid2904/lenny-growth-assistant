import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message } from '../types/api';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const citations = message.metadata?.citations || [];
  const isRefusal = message.content.includes("couldn't find enough relevant material");

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
