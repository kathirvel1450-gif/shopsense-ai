import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App.jsx';
import { ConversationProvider } from './hooks/ConversationContext.jsx';
import './style.css';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter><ConversationProvider><App /></ConversationProvider></BrowserRouter>
  </React.StrictMode>,
);
