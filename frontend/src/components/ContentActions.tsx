interface ContentActionsProps {
  onActionClick: (prompt: string) => void;
  disabled: boolean;
}

export function ContentActions({ onActionClick, disabled }: ContentActionsProps) {
  const actions = [
    {
      label: 'Ship 30 Essay',
      prompt: 'Turn this into a Ship 30 for 30 essay.',
      description: 'Generate a long-form essay (~1,250 words)',
    },
    {
      label: 'LinkedIn Post',
      prompt: 'Summarize this as a LinkedIn post.',
      description: 'Create a LinkedIn-style post',
    },
    {
      label: 'X Thread',
      prompt: 'Write this as a Twitter thread.',
      description: 'Create an X/Twitter thread',
    },
    {
      label: 'Concise Insight',
      prompt: 'Write a concise product insight.',
      description: 'Generate a brief insight',
    },
    {
      label: 'HTML Artifact',
      prompt: 'Create an HTML artifact visual summary of this framework.',
      description: 'Generate a visual HTML/CSS artifact',
    },
    {
      label: 'Markdown Artifact',
      prompt: 'Create a markdown artifact structured guide for this.',
      description: 'Generate a structured Markdown artifact',
    },
  ];

  return (
    <div className="border-b border-gray-200 p-4 bg-gray-50">
      <div className="text-sm font-medium text-gray-700 mb-3">
        Quick Actions:
      </div>
      <div className="flex flex-wrap gap-2">
        {actions.map((action) => (
          <button
            key={action.label}
            onClick={() => onActionClick(action.prompt)}
            disabled={disabled}
            className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title={action.description}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}
