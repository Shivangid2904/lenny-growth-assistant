# Design: Lenny Growth Assistant UI/UX

## 1. Design Philosophy

The Lenny Growth Assistant interface prioritizes **information density, grounding visibility, and professional utility** over decorative UI. The design is optimized for product managers who need quick, trustworthy answers with clear source attribution, not conversational chit-chat.

**Core Principles:**
- **Grounding First**: Citations and source evidence are always visible, never hidden
- **Artifact-Ready**: Dual-pane layout supports simultaneous chat and document viewing
- **Professional Minimalism**: Clean typography, high contrast, no unnecessary animations
- **Action-Oriented**: Explicit content generation actions are surface-level, not buried in prompts
- **Error Transparency**: Refusals and errors appear as normal assistant responses, not red warning banners

---

## 2. Layout Architecture

### Overall Structure

```
+-----------------------------------------------------------------------+
| Header: Lenny Growth Assistant                                        |
| "Grounded insights from Lenny's Podcast transcripts"                 |
+-----------------------------------------------------------------------+
|                                                                       |
|  +-------------------+  +-------------------+                        |
|  |                   |  |                   |                        |
|  |   Chat Pane       |  |  Artifact Pane    |                        |
|  |                   |  |  (when active)    |                        |
|  |   - Messages      |  |                   |                        |
|  |   - Composer      |  |   - Title         |                        |
|  |   - Empty State   |  |   - Content       |                        |
|  |   - Error Display |  |   - Security     |                        |
|  |                   |  |     indicator     |                        |
|  +-------------------+  +-------------------+                        |
|                                                                       |
+-----------------------------------------------------------------------+
```

### Responsive Behavior

- **Desktop (>768px)**: Side-by-side dual-pane layout. Chat pane takes 60% width, artifact pane 40% (when active)
- **Mobile (<768px)**: Single-column stack. Artifact pane slides in as an overlay or appears below chat when active
- **Fallback**: If JavaScript fails, a basic HTML form submits messages synchronously (progressive enhancement)

---

## 3. Chat Interface Design

### Message Hierarchy

```
User Message
├─ Right-aligned, blue background
├─ No citation needed (user input)
└─ Timestamp

Assistant Message  
├─ Left-aligned, white background with subtle border
├─ Markdown rendering (headings, bullets, bold)
├─ Inline citations [Episode Title • Guest Name]
├─ Timestamp
└─ Action buttons (Copy, Regenerate - when available)

System/Refusal Message
├─ Left-aligned, gray background
├─ Normal assistant appearance (not red error banner)
├─ Clear refusal language: "I couldn't find enough relevant material..."
└─ Suggested follow-up actions when appropriate
```

### Citation Presentation

Citations are rendered as **clickable inline badges** within the assistant response:

```markdown
According to Brian Balfour [Product-Market Fit • Brian Balfour], the Four Fits framework...
```

**Interaction:** Clicking a citation opens the original episode source URL in a new tab (if available) or shows episode metadata in a tooltip.

**Why Inline?** Inline citations maintain reading flow while grounding every claim. Separate reference sections force users to scroll away from context.

---

## 4. Empty States

### Initial Empty State (No Messages)

```
+-------------------------------------------------------+
|                                                       |
|              Lenny Growth Assistant                  |
|                                                       |
|    Ask about product strategy, growth loops,          |
|    pricing, onboarding, or any PM topic               |
|                                                       |
|    Example questions:                                 |
|    [What is the Four Fits framework?]                |
|    [How do I measure early-stage retention?]          |
|    [What's the difference between PLG and sales-led?] |
|                                                       |
+-------------------------------------------------------+
```

**Rationale:** Provides immediate guidance on what kinds of questions are answerable without forcing users to read documentation first.

### Refusal Empty State (After Unsupported Query)

```
+-------------------------------------------------------+
|                                                       |
|    I couldn't find enough relevant material in        |
|    Lenny's Podcast transcripts to answer that.        |
|                                                       |
|    Try asking about:                                  |
|    [Product-market fit]                               |
|    [Growth loops vs funnels]                          |
|    [Product-led growth tactics]                       |
|                                                       |
+-------------------------------------------------------+
```

**Rationale:** Refusals are framed as **gaps in the corpus**, not system failures. Suggested topics guide users toward answerable questions.

---

## 5. Composer & Input Design

### Chat Composer

```
+-------------------------------------------------------+
| [How should I think about pricing for B2B SaaS?]     |
|                                                       |
|  [Send]              [Essay] [LinkedIn] [Thread]     |
+-------------------------------------------------------+
```

**Design Decisions:**
- **Multi-line textarea**: Supports complex questions without manual line breaks
- **Explicit Action Buttons**: Content generation skills are surface-level buttons, not hidden behind prompt engineering
- **Enter-to-Send**: Single-line questions submit on Enter; Shift+Enter for new line
- **Disabled State**: Buttons grayed out during streaming to prevent duplicate submissions

### Why Explicit Action Buttons?

The Ship30 skill and content generation are **first-class features**, not incidental prompt tricks. Surface-level buttons make these capabilities discoverable without requiring users to memorize magic phrases like "Write a Ship30 essay about..."

---

## 6. Artifact Viewer Design

### Artifact Pane Layout

```
+-------------------------------------------------------+
| [Back to Chat]  Product-Market Fit Framework         |
|                                                       |
| +---------------------------------------------------+ |
| |                                                   | |
| |   ## The Four Fits Framework                     | |
| |                                                   | |
| |   According to Brian Balfour...                  | |
| |                                                   | |
| |   ### Market-Product Fit                         | |
| |   - Cohort retention curve                       | |
| |   - Lifetime value impact                         | |
| |                                                   | |
| +---------------------------------------------------+ |
|                                                       |
| 🔒 Rendered in secure sandbox • No scripts allowed   |
+-------------------------------------------------------+
```

### Security Indicator

The **🔒 secure sandbox badge** is always visible in the artifact pane header. It communicates to evaluators and users that:

- HTML/CSS is rendered via `iframe srcdoc` with `sandbox="allow-same-origin"`
- JavaScript execution is blocked
- External resource loading is blocked
- This is a deliberate security boundary, not an oversight

### Artifact Types & Rendering

| Type | Rendering | Security |
|------|-----------|----------|
| **Markdown** | React-markdown with remark-gfm | Server-side sanitization not required (no HTML) |
| **HTML** | iframe srcdoc with sandbox | Server-side sanitization + client sandbox |
| **CSS** | Inline `<style>` blocks within HTML | Sanitized to block `@import` and external URLs |

---

## 7. Error & Refusal States

### Error Display (Non-Fatal Errors)

```
+-------------------------------------------------------+
| ⚠️ Backend temporarily unavailable                    |
|                                                       |
|    The service is experiencing issues. Retrying...    |
|                                                       |
|    [Retry] [Dismiss]                                  |
+-------------------------------------------------------+
```

**Placement:** Top of chat pane, dismissible, does not block message composition.

**When Shown:** Network errors, provider timeouts, temporary database issues.

### Refusal Display (Grounding Refusal)

Refusals **do not** use red error banners. They appear as normal assistant messages:

```
Assistant: I couldn't find enough relevant material in Lenny's Podcast 
transcripts to answer that reliably. The available episodes don't cover 
[this specific topic] in depth.
```

**Rationale:** Refusals are **correct behavior**, not errors. Red error banners would signal a system problem rather than a deliberate grounding guardrail.

---

## 8. Content Generation Actions

### Action Buttons Below Messages

When an assistant message contains actionable content, action buttons appear:

```
+-------------------------------------------------------+
| According to Brian Balfour, the Four Fits framework...|
|                                                       |
| [Turn into Ship30 Essay] [LinkedIn Post] [X Thread]   |
+-------------------------------------------------------+
```

**Why Below Messages?** Actions are context-dependent. They appear only when relevant to the current conversation turn, reducing UI clutter.

### Skill Detection Logic

The backend uses **intent detection** on the user's input to route to specialized skills:

- `"Write a Ship30 essay about..."` → Ship30 skill
- `"Turn this into a LinkedIn post"` → LinkedIn skill  
- `"Create an X thread"` → Thread skill
- `"Summarize as a concise insight"` → Concise insight skill

Fallback: Default grounded Q&A if no intent matches.

---

## 9. Streaming Experience

### Token-by-Token Streaming

```
User: What is product-market fit?

Assistant: [typing indicator] Product-market fit...

[streaming] Product-market fit is when...
[streaming] ...a product resonates...
[streaming] ...with its target market.

[citation] [Brian Balfour • Product-Market Fit]
```

**UX Decisions:**
- **Typing Indicator**: Brief spinner while first token arrives (~200-500ms)
- **Smooth Streaming**: Tokens append in real-time; no artificial delays
- **Citation Appearance**: Citations appear after streaming completes (in `done` event)
- **Artifact Trigger**: If skill generates artifact, artifact pane slides in automatically

### Why SSE Over WebSocket?

Server-Sent Events (SSE) are sufficient for **unidirectional streaming** (server → client). WebSockets add bidirectional complexity without benefit for this use case.

---

## 10. Accessibility & Keyboard Navigation

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Send message (when composer focused) |
| `Shift+Enter` | New line in composer |
| `Escape` | Close artifact pane (if open) |
| `Ctrl/Cmd+K` | Focus composer |
| `Ctrl/Cmd+/` | Show keyboard shortcuts |

### Screen Reader Support

- **Semantic HTML**: Proper heading hierarchy (`h1`, `h2`, `h3`)
- **ARIA Labels**: Action buttons include descriptive labels
- **Focus Management**: Composer auto-focuses after message send
- **Live Regions**: Streaming content marked with `aria-live="polite"`

---

## 11. Color & Typography

### Color Palette

| Element | Color | Purpose |
|---------|-------|---------|
| **Primary** | Blue-600 (`#2563eb`) | User messages, primary actions |
| **Background** | Gray-50 (`#f9fafb`) | Page background |
| **Surface** | White (`#ffffff`) | Message bubbles, panels |
| **Text Primary** | Gray-900 (`#111827`) | Headings, body text |
| **Text Secondary** | Gray-600 (`#4b5563`) | Metadata, timestamps |
| **Error** | Red-600 (`#dc2626`) | Non-fatal errors only |
| **Success** | Green-600 (`#16a34a`) | Successful operations |

### Typography

- **Font Family**: System sans-serif (Inter, San Francisco, Segoe UI)
- **Headings**: Bold, 1.25x–2x base size
- **Body**: Regular, 1x base size, 1.5 line height
- **Code**: Monospace, 0.9x base size, gray background

**Rationale:** System fonts ensure fast loading and native OS consistency. High contrast ratios (WCAG AA compliant) ensure readability.

---

## 12. Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| **Mobile** | < 640px | Single column, artifact overlay |
| **Tablet** | 640px–1024px | Single column, artifact below chat |
| **Desktop** | > 1024px | Dual-pane side-by-side |

---

## 13. Performance Considerations

### Frontend Optimization

- **Code Splitting**: React lazy loading for artifact viewer component
- **Bundle Size**: < 400KB gzipped for initial load
- **Image Optimization**: No external images; all icons inline SVG
- **CSS-in-JS**: Tailwind CSS with JIT compilation (build-time)

### Streaming Performance

- **Token Buffering**: Tokens batched in 50ms chunks to reduce DOM updates
- **Virtual Scrolling**: Not implemented (chat history limited to 10 messages)
- **Artifact Caching**: Artifacts stored in Redux/local state to avoid re-fetching

---

## 14. Future Enhancement Opportunities

These are **out of scope** for the MVP but designed for future iteration:

- **Dark Mode**: CSS variables would enable theme switching
- **Export Artifacts**: Download as .md or .html files
- **Session Sharing**: Shareable links to public sessions (read-only)
- **Advanced Filtering**: Filter conversations by topic, guest, or date
- **Analytics Dashboard**: Visualize retrieval quality and usage patterns

---

## 15. Design Rationale Summary

| Decision | Rationale |
|---------|-----------|
| **Dual-pane layout** | Enables simultaneous chat and document viewing without context switching |
| **Inline citations** | Maintains reading flow while grounding every claim |
| **Explicit action buttons** | Makes content generation discoverable without prompt engineering |
| **Refusals as normal messages** | Correct behavior, not system errors |
| **Secure sandbox badge** | Communicates security boundary to evaluators and users |
| **Minimal animations** | Prioritizes information density over decorative effects |
| **System fonts** | Fast loading, native OS consistency, no external dependencies |
