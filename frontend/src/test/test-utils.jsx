import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ConversationProvider } from '../hooks/ConversationContext.jsx';
import App from '../App.jsx';

export function renderApp(path = '/') {
  window.history.replaceState({}, '', path);
  return render(<MemoryRouter initialEntries={[path]}><ConversationProvider><App /></ConversationProvider></MemoryRouter>);
}
