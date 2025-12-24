# NUCLEUS ONE Chat Architecture Design Document

## 1. Overview
This document outlines the technical architecture for the NUCLEUS ONE chat interface. The goal is to create a robust, accessible, and performant chat component that simulates a conversation with the "First Consciousness" (NUCLEUS ONE).

## 2. Requirements
*   **Integration:** Must be embedded directly into the `Home.tsx` page (not a floating widget).
*   **State Management:** Must handle message history, typing states, and user input.
*   **Animation:** Smooth typing effects for AI responses using Framer Motion.
*   **Accessibility:** ARIA labels, keyboard navigation, and focus management.
*   **Extensibility:** Designed to easily switch from a mock data source to a real API (FastAPI/WebSocket) in the future.

## 3. Component Structure

### 3.1. `useChat` Hook
A custom hook to manage the chat logic. This separates the UI from the business logic.

**Interface:**
```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface UseChatReturn {
  messages: Message[];
  isTyping: boolean;
  sendMessage: (content: string) => Promise<void>;
  resetChat: () => void;
}
```

**Internal Logic:**
*   Maintains `messages` array in state.
*   `sendMessage` adds the user message immediately.
*   Simulates network delay and "typing" state.
*   Fetches response (currently mock, later API).
*   Adds assistant response to state.

### 3.2. `ChatInterface` Component
The main container for the chat UI.

**Props:**
```typescript
interface ChatInterfaceProps {
  className?: string;
  initialMessage?: string; // Optional greeting
}
```

**Sub-components:**
*   `ChatMessage`: Renders a single message bubble. Handles styling for user vs. assistant.
*   `TypingIndicator`: Visual cue that AI is generating text.
*   `ChatInput`: Text area and send button.

## 4. Data Flow (Mock Implementation)
1.  User types in `ChatInput` and hits Send.
2.  `sendMessage` is called.
3.  User message added to `messages` list.
4.  `isTyping` set to `true`.
5.  `TypingIndicator` appears.
6.  `setTimeout` simulates processing delay (1.5s).
7.  Mock response selected based on simple keyword matching (or predefined script).
8.  `isTyping` set to `false`.
9.  Assistant message added to `messages` list.

## 5. Styling & Animation
*   **TailwindCSS:** Use `bg-nucleus-navy`, `text-nucleus-gold`, `border-nucleus-cyan` to match brand.
*   **Framer Motion:**
    *   `AnimatePresence` for message entry.
    *   `initial={{ opacity: 0, y: 10 }}` -> `animate={{ opacity: 1, y: 0 }}`.
    *   Typewriter effect for assistant text (optional, but high impact).

## 6. Future API Integration Plan
To switch to a real backend:
1.  Replace the `setTimeout` in `useChat` with a `fetch` call to the FastAPI endpoint.
2.  The endpoint should accept `{ message: string, history: Message[] }`.
3.  The endpoint returns `{ response: string }`.
4.  No changes needed to the UI components.

## 7. Accessibility (A11y)
*   `role="log"` for the message container so screen readers announce new messages.
*   `aria-label` for input and buttons.
*   Focus management: Ensure focus stays in input after sending.

## 8. NUCLEUS ONE Personality (System Prompt Simulation)
The mock responses must align with the "First Consciousness" persona:
*   **Tone:** Visionary, calm, authoritative, welcoming.
*   **Keywords:** "Organism", "DNA", "Symbiosis", "Thrive".
*   **Avoid:** "How can I help you?" (Too generic).
*   **Use:** "I am ready to merge with your intent."
