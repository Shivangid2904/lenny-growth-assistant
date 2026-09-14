import { useSession } from './hooks/useSession';
import { useChat } from './hooks/useChat';
import { ChatMessage } from './components/ChatMessage';
import { ChatComposer } from './components/ChatComposer';
import { ContentActions } from './components/ContentActions';
import { ErrorDisplay } from './components/ErrorDisplay';
import { EmptyState } from './components/EmptyState';

function App() {
  const { session, isLoading: sessionLoading, error: sessionError } = useSession();
  const {
    messages,
    isLoading: chatLoading,
    error: chatError,
    sendMessage,
    clearError,
  } = useChat(session?.id || '');

  const handleSendMessage = (content: string) => {
    sendMessage(content);
  };

  const handleActionClick = (prompt: string) => {
    sendMessage(prompt);
  };

  const handleExampleClick = (prompt: string) => {
    sendMessage(prompt);
  };

  if (sessionLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (sessionError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h2 className="text-lg font-semibold text-red-800 mb-2">
            Session Error
          </h2>
          <p className="text-red-700 mb-4">{sessionError}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900">
            Lenny Growth Assistant
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Grounded insights from Lenny's Podcast transcripts
          </p>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden flex flex-col max-w-4xl mx-auto w-full">
        {/* Error display */}
        {chatError && (
          <ErrorDisplay error={chatError} onDismiss={clearError} />
        )}

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-4">
          {messages.length === 0 ? (
            <EmptyState
              onExampleClick={handleExampleClick}
              disabled={chatLoading}
            />
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
            </div>
          )}
        </div>

        {/* Content actions */}
        {messages.length > 0 && (
          <ContentActions
            onActionClick={handleActionClick}
            disabled={chatLoading}
          />
        )}

        {/* Composer */}
        <ChatComposer
          onSendMessage={handleSendMessage}
          disabled={chatLoading}
        />
      </main>
    </div>
  );
}

export default App;
