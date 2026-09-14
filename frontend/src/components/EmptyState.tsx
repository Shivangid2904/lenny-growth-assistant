interface EmptyStateProps {
  onExampleClick: (prompt: string) => void;
  disabled: boolean;
}

export function EmptyState({ onExampleClick, disabled }: EmptyStateProps) {
  const examples = [
    "What are the biggest reasons startups fail to retain users?",
    "How should I think about product-market fit?",
    "Turn this into a Ship 30 for 30 essay.",
  ];

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-2xl">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Welcome to Lenny Growth Assistant
        </h2>
        <p className="text-gray-600 mb-8">
          Ask about product management, growth strategies, or startup advice. 
          All responses are grounded in Lenny's Podcast transcripts.
        </p>
        <div className="space-y-3">
          <div className="text-sm font-medium text-gray-700 mb-3">
            Try asking:
          </div>
          {examples.map((example, index) => (
            <button
              key={index}
              onClick={() => onExampleClick(example)}
              disabled={disabled}
              className="block w-full text-left px-4 py-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <span className="text-gray-700">{example}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
