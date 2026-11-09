import { createContext, useContext, useMemo, useState } from 'react';

const ConversationContext = createContext(null);
const STORAGE_KEY = 'shopsense-assistant-session-v1';

export function maskDisplayText(value = '') {
  return String(value)
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, '[EMAIL]')
    .replace(/\b(?:ORD|ORDER|CUS|CUSTOMER)[-_ ]?[A-Z0-9]{4,}\b/gi, '[IDENTIFIER]')
    .replace(/(?:\+?\d[\d ().-]{7,}\d)/g, '[PHONE]');
}

function readSaved() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || '{}');
    return { conversationId: saved.conversationId || null, messages: Array.isArray(saved.messages) ? saved.messages.map((message) => ({ ...message, text: maskDisplayText(message.text || '') })) : [] };
  } catch { return { conversationId: null, messages: [] }; }
}

export function ConversationProvider({ children }) {
  const [session, setSession] = useState(readSaved);
  const update = (next) => setSession((current) => {
    const value = typeof next === 'function' ? next(current) : next;
    const safe = { ...value, messages: value.messages.map((message) => ({ ...message, text: maskDisplayText(message.text) })) };
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(safe)); } catch { /* Session storage is optional. */ }
    return safe;
  });
  const value = useMemo(() => ({ ...session, update }), [session]);
  return <ConversationContext.Provider value={value}>{children}</ConversationContext.Provider>;
}

export const useConversation = () => useContext(ConversationContext);
