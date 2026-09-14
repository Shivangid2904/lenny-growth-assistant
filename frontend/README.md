# Lenny Growth Assistant - Frontend

React + Vite frontend for the Lenny Growth Assistant application.

## Technology Stack

- **React 18**: UI library
- **Vite**: Build tool and dev server
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **react-markdown**: Markdown rendering
- **remark-gfm**: GitHub Flavored Markdown support
- **Vitest**: Testing framework
- **@testing-library/react**: Component testing

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start development server:
   ```bash
   npm run dev
   ```

3. Open browser to `http://localhost:5173`

### Build

```bash
npm run build
```

The production build will be in the `dist/` directory.

### Testing

```bash
npm test -- --run
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── ChatMessage.tsx  # Message display with markdown
│   │   ├── ChatComposer.tsx # Message input form
│   │   ├── ContentActions.tsx # Quick action buttons
│   │   ├── ErrorDisplay.tsx # Error banner
│   │   └── EmptyState.tsx   # Welcome screen
│   ├── hooks/              # Custom React hooks
│   │   ├── useChat.ts      # Chat logic and SSE handling
│   │   └── useSession.ts   # Session management
│   ├── lib/                # Utilities
│   │   └── api.ts          # API client and SSE parser
│   ├── types/              # TypeScript types
│   │   └── api.ts          # API type definitions
│   ├── test/               # Test setup
│   │   └── setup.ts        # Vitest configuration
│   ├── App.tsx             # Main application
│   ├── main.tsx            # Entry point
│   └── index.css           # Global styles
├── public/                 # Static assets
├── index.html              # HTML template
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Dependencies
```

## Key Features

### SSE Streaming

The frontend uses Server-Sent Events for real-time streaming:

- **Token Events**: Progressive content updates
- **Done Events**: Completion with citations and metadata
- **Error Events**: System failure handling

### Grounded Refusal Handling

Grounded refusals (no eligible evidence) are rendered as normal assistant messages with:
- Standard assistant bubble styling
- Optional "No matching source material" cue
- NOT treated as errors

### Session Management

- Automatic session creation on first load
- Session persistence via localStorage
- Session recovery on page reload
- Automatic session cleanup on 404 errors

### Content Actions

Quick action buttons for content generation:
- Ship 30 Essay
- LinkedIn Post
- X Thread
- Concise Insight

These route through the backend Ship30 skill system.

### Markdown Rendering

Full markdown support with:
- Headings and paragraphs
- Lists (ordered and unordered)
- Bold and emphasis
- Links (with external link handling)
- Code blocks
- Tables

### Citation Display

Citations are rendered with:
- Episode title
- Guest name
- Source URL
- Chunk index
- Optional distance metric

## API Integration

The frontend communicates with the backend via:

1. **Session API**: `POST /api/sessions`, `GET /api/sessions/{id}`
2. **Chat API**: `POST /api/sessions/{id}/messages` (SSE streaming)

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

## Error Handling

The frontend distinguishes between:

1. **Grounded Refusals**: Normal assistant response with subtle cue
2. **System Errors**: Red error banner with dismiss button
3. **Network Errors**: API error handling with user-friendly messages

## Responsive Design

The application is fully responsive:

- **Desktop**: Centered content with comfortable width
- **Mobile**: Full-width with no horizontal overflow
- **Touch-friendly**: Accessible buttons and inputs

## Security Considerations

- No direct HTML injection from assistant responses
- Markdown rendering via react-markdown (safe by default)
- External links open in new tabs with `rel="noopener noreferrer"`
- Session IDs stored in localStorage (no sensitive data)
- No credential exposure in client-side code

## Environment Variables

Create a `.env` file in the frontend directory:

```bash
VITE_API_BASE_URL=/api
```

For direct backend connection (no proxy):

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

## Testing Strategy

### Component Tests

- ChatMessage rendering (user/assistant)
- Markdown rendering
- Citation display
- Refusal handling
- Error states

### Hook Tests

- useChat message sending
- SSE event handling
- Duplicate submission prevention
- Error handling
- Session management

### Integration Goals

Tests mock the backend API to ensure:
- No dependency on live services
- Fast test execution
- Reliable test results
- Edge case coverage

## Performance

- Code splitting via Vite
- Lazy loading for large dependencies
- Optimized production build
- Tree shaking for unused code
- Efficient SSE parsing with minimal re-renders

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES2020+ features
- CSS Grid and Flexbox
- Server-Sent Events API
