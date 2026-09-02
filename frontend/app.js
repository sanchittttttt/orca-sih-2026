const DEFAULT_LOCATION = { lat: 16.99, lon: 73.31 };

function getSelectedLocation() {
  const picker = document.getElementById('location-picker');
  if (!picker || !picker.value) {
    return { ...DEFAULT_LOCATION };
  }

  const [lat, lon] = picker.value.split(',').map(Number);
  return {
    lat: Number(lat),
    lon: Number(lon)
  };
}

const personaQueries = {
  Fisherman: [
    'Is it safe to go fishing tomorrow near Ratnagiri?',
    'Where are the nearest good fishing zones?',
    'What are the current wave conditions near the Konkan coast?',
    'Are there any moderate weather alerts near Ratnagiri?'
  ],
  'Disaster Management Agency': [
    'Are there any active cyclone alerts near the Indian coast?',
    'What are the latest coastal threat conditions around the west coast?',
    'Is there a high-risk weather pattern developing offshore?',
    'Show me any lightning or cyclone warnings in the region.'
  ],
  Researcher: [
    "What's the current chlorophyll and SST data for the Kerala coast?",
    'Compare the recent marine conditions along the western coast.',
    'Is the ocean environment showing strong PFZ activity near the shelf break?',
    'What evidence supports the current marine risk profile for this area?'
  ],
  'Maritime/Coastal Authority': [
    'Show me current wave conditions along the Konkan coast.',
    'What sea state and wind conditions should mariners expect today?',
    'Are there any active hazards for vessels operating offshore?',
    'Summarize the present coastal risk and recommended actions.'
  ]
};

const appState = {
  activePersona: 'Fisherman',
  sessionId: null,
  loadingMessageEl: null,
  expandedPayload: null
};

function formatConversationTimestamp(value) {
  if (!value) return 'Unknown time';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short'
  });
}

function showScreen(screenId) {
  const intro = document.getElementById('intro-screen');
  const chat = document.getElementById('chat-screen');

  if (screenId === 'intro') {
    intro.classList.remove('hidden');
    chat.classList.add('hidden');
  } else {
    intro.classList.add('hidden');
    chat.classList.remove('hidden');
  }
}

function renderPersonaSelector() {
  const cards = document.querySelectorAll('.persona-card');
  cards.forEach((card) => {
    const isActive = card.dataset.persona === appState.activePersona;
    card.classList.toggle('selected', isActive);
  });
}

function renderSuggestedQueries() {
  const container = document.getElementById('suggestion-row');
  const items = personaQueries[appState.activePersona] || [];
  container.innerHTML = items
    .slice(0, 4)
    .map((query) => `<button type="button" class="suggestion-chip" data-query="${escapeHtml(query)}">${escapeHtml(query)}</button>`)
    .join('');

  container.querySelectorAll('.suggestion-chip').forEach((button) => {
    button.addEventListener('click', () => {
      const input = document.getElementById('chat-input');
      input.value = button.dataset.query;
      sendQuery(button.dataset.query, 'suggested');
    });
  });

  document.getElementById('persona-label').textContent = appState.activePersona;
}

function resetChatSession() {
  appState.sessionId = null;
  const chatMessages = document.getElementById('chat-messages');
  if (chatMessages) {
    chatMessages.innerHTML = '';
  }

  const input = document.getElementById('chat-input');
  if (input) {
    input.value = '';
  }

  renderSuggestedQueries();
}

function renderExamples() {
  const container = document.getElementById('example-row');
  const examples = Array.isArray(window.mockExamples) ? window.mockExamples : [];
  if (!examples.length) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = examples
    .map((example) => `
      <button type="button" class="example-button" data-example-id="${example.id}">
        <strong>Example</strong>
        <span>${escapeHtml(example.title)}</span>
      </button>
    `)
    .join('');

  container.querySelectorAll('.example-button').forEach((button) => {
    button.addEventListener('click', () => {
      const example = examples.find((item) => item.id === button.dataset.exampleId);
      if (!example) return;
      renderExampleResponse(example);
    });
  });
}

function renderExampleResponse(example) {
  const chatMessages = document.getElementById('chat-messages');
  const message = {
    source: 'assistant',
    payload: example,
    isExample: true,
    isLive: false
  };
  const bubble = buildAssistantBubble(message);
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  if (window.voice && !window.voice.isMuted) {
    window.voice.speak(example.explanation_text);
  }
}

function formatRiskFromComponent(payload) {
  if (!payload || !payload.ui_json || !Array.isArray(payload.ui_json.components)) return null;
  const risk = payload.ui_json.components.find((component) => component.type === 'risk-card');
  if (!risk || !risk.data) return null;
  const level = String(risk.data.level || '').toUpperCase();
  if (!level) return null;
  return {
    level,
    className: window.riskBadgeClass ? window.riskBadgeClass(level) : 'moderate'
  };
}

function buildAssistantBubble(message) {
  const wrapper = document.createElement('div');
  wrapper.className = 'message assistant';

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';

  const meta = document.createElement('div');
  meta.className = 'message-meta';

  const tag = document.createElement('span');
  const tagClass = message.isExample ? 'example' : message.isHistory ? 'history' : 'live';
  const tagText = message.isExample ? 'Example' : message.isHistory ? 'History' : 'Live';
  tag.className = `message-tag ${tagClass}`;
  tag.textContent = tagText;
  meta.appendChild(tag);

  const risk = formatRiskFromComponent(message.payload);
  if (risk) {
    const badge = document.createElement('span');
    badge.className = `message-risk ${risk.className}`;
    badge.textContent = risk.level;
    meta.appendChild(badge);
  }

  const text = document.createElement('div');
  text.className = 'message-text';
  text.textContent = message.payload.explanation_text || 'No explanation text returned.';

  const actions = document.createElement('div');
  actions.className = 'message-actions';
  const expandButton = document.createElement('button');
  expandButton.type = 'button';
  expandButton.className = 'expand-button';
  expandButton.textContent = 'Expand';
  expandButton.addEventListener('click', () => openDetailModal(message.payload));
  actions.appendChild(expandButton);

  bubble.appendChild(meta);
  bubble.appendChild(text);
  bubble.appendChild(actions);
  wrapper.appendChild(bubble);
  return wrapper;
}

function buildUserBubble(text) {
  const wrapper = document.createElement('div');
  wrapper.className = 'message user';

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';

  const textNode = document.createElement('div');
  textNode.className = 'message-text';
  textNode.textContent = text;

  bubble.appendChild(textNode);
  wrapper.appendChild(bubble);
  return wrapper;
}

async function openHistoryModal() {
  const modal = document.getElementById('history-modal');
  modal.classList.remove('hidden');
  modal.setAttribute('aria-hidden', 'false');
  await loadSessionList();
}

function closeHistoryModal() {
  const modal = document.getElementById('history-modal');
  modal.classList.add('hidden');
  modal.setAttribute('aria-hidden', 'true');
}

async function loadSessionList() {
  const listEl = document.getElementById('history-session-list');

  try {
    const response = await fetch('http://localhost:8081/api/sessions');
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    const sessions = await response.json();
    const items = Array.isArray(sessions) ? sessions : [];

    if (!items.length) {
      listEl.innerHTML = '<div class="history-empty">No past conversations yet.</div>';
      return;
    }

    listEl.innerHTML = items
      .map((session) => `
        <button type="button" class="history-session-row" data-session-id="${escapeHtml(session.sessionId)}">
          <span class="history-preview">${escapeHtml(session.preview || '(empty conversation)')}</span>
          <span class="history-date">${escapeHtml(formatConversationTimestamp(session.createdAt))}</span>
        </button>
      `)
      .join('');

    listEl.querySelectorAll('.history-session-row').forEach((button) => {
      button.addEventListener('click', async () => {
        const sessionId = button.dataset.sessionId;
        await loadConversation(sessionId);
        closeHistoryModal();
      });
    });
  } catch (error) {
    console.error('Failed to load saved conversations:', error);
    listEl.innerHTML = '<div class="history-empty">Unable to load past conversations right now.</div>';
  }
}

async function loadConversation(sessionId) {
  const chatMessages = document.getElementById('chat-messages');
  chatMessages.innerHTML = '';

  try {
    const response = await fetch(`http://localhost:8081/api/conversations/${encodeURIComponent(sessionId)}`);
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    const messages = await response.json();
    if (!Array.isArray(messages)) {
      throw new Error('Conversation payload was not an array.');
    }

    messages.forEach((message) => {
      if (message.role === 'user') {
        chatMessages.appendChild(buildUserBubble(String(message.content || '')));
        return;
      }

      if (message.role === 'assistant') {
        let payload = null;
        try {
          payload = JSON.parse(message.content);
        } catch (error) {
          console.warn('Saved assistant content could not be parsed as JSON:', error);
          payload = {
            explanation_text: String(message.content || 'Assistant response unavailable.'),
            ui_json: { components: [] }
          };
        }

        if (!payload || typeof payload !== 'object') {
          return;
        }

        chatMessages.appendChild(buildAssistantBubble({
          source: 'assistant',
          payload,
          isExample: false,
          isHistory: true,
          isLive: false
        }));
      }
    });

    appState.sessionId = sessionId;
    chatMessages.scrollTop = chatMessages.scrollHeight;
  } catch (error) {
    console.error('Failed to load conversation history:', error);
    chatMessages.appendChild(buildUserBubble('The saved conversation could not be reopened right now.'));
  }
}

function setLoadingState(active, text = 'Checking conditions...') {
  const chatMessages = document.getElementById('chat-messages');
  if (active) {
    if (appState.loadingMessageEl) return;
    const loader = document.createElement('div');
    loader.className = 'message assistant';
    loader.innerHTML = `
      <div class="message-bubble">
        <div class="loading-row">
          <span class="spinner" aria-hidden="true"></span>
          <span>${escapeHtml(text)}</span>
        </div>
      </div>
    `;
    chatMessages.appendChild(loader);
    appState.loadingMessageEl = loader;
    chatMessages.scrollTop = chatMessages.scrollHeight;
    if (window.voice && !window.voice.isMuted) {
      window.voice.announceLoading();
    }
  } else if (appState.loadingMessageEl) {
    appState.loadingMessageEl.remove();
    appState.loadingMessageEl = null;
  }
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function sendQuery(query, source) {
  const cleanQuery = String(query || '').trim();
  if (!cleanQuery) return;

  const input = document.getElementById('chat-input');
  if (input) input.value = '';

  const chatMessages = document.getElementById('chat-messages');
  chatMessages.appendChild(buildUserBubble(cleanQuery));
  chatMessages.scrollTop = chatMessages.scrollHeight;
  setLoadingState(true, 'Checking conditions...');

  const payload = {
    query: cleanQuery,
    location: getSelectedLocation(),
    sessionId: appState.sessionId || undefined
  };

  try {
    const response = await fetch('http://localhost:8081/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    const data = await response.json();
    if (data && data.sessionId) {
      appState.sessionId = data.sessionId;
    }

    const assistantMessage = {
      source: 'assistant',
      payload: data,
      isExample: false,
      isLive: true
    };

    const bubble = buildAssistantBubble(assistantMessage);
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    if (data && data.explanation_text && window.voice && !window.voice.isMuted) {
      window.voice.speak(data.explanation_text);
    }
  } catch (error) {
    console.error('Chat request failed:', error);
    const fallback = document.createElement('div');
    fallback.className = 'message assistant';
    fallback.innerHTML = `
      <div class="message-bubble">
        <div class="message-text">The live service is unavailable right now. Use an example response or try again in a moment.</div>
      </div>
    `;
    chatMessages.appendChild(fallback);
  } finally {
    setLoadingState(false);
  }
}

function openDetailModal(payload) {
  if (!payload) return;
  appState.expandedPayload = payload;
  const modal = document.getElementById('detail-modal');
  const content = document.getElementById('modal-content');
  content.innerHTML = '';

  const introLine = document.createElement('div');
  introLine.className = 'detail-panel';
  introLine.innerHTML = `<h4>Summary</h4><p>${escapeHtml(payload.explanation_text || 'No explanation text available.')}</p>`;
  content.appendChild(introLine);

  const components = Array.isArray(payload.ui_json && payload.ui_json.components) ? payload.ui_json.components : [];
  if (!components.length) {
    content.insertAdjacentHTML('beforeend', '<div class="detail-panel"><h4>Components</h4><p>No components available.</p></div>');
  } else {
    components.forEach((component) => {
      const type = component && component.type;
      const renderer = window.ComponentRegistry && window.ComponentRegistry[type];
      if (!renderer) {
        console.warn(`Skipping unrecognized component type: ${type}`);
        return;
      }

      const markup = renderer(component.data || {});
      content.insertAdjacentHTML('beforeend', markup);
    });
  }

  modal.classList.remove('hidden');
  modal.setAttribute('aria-hidden', 'false');
}

function closeDetailModal() {
  const modal = document.getElementById('detail-modal');
  modal.classList.add('hidden');
  modal.setAttribute('aria-hidden', 'true');
}

function wireEvents() {
  document.getElementById('chat-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const input = document.getElementById('chat-input');
    sendQuery(input.value, 'typed');
  });

  document.getElementById('switch-persona-button').addEventListener('click', () => {
    showScreen('intro');
  });

  document.getElementById('new-chat-button').addEventListener('click', () => {
    resetChatSession();
  });

  document.getElementById('open-history-button').addEventListener('click', openHistoryModal);
  document.getElementById('close-history-button').addEventListener('click', closeHistoryModal);
  document.querySelector('[data-close-history="true"]').addEventListener('click', closeHistoryModal);

  document.getElementById('close-modal-button').addEventListener('click', closeDetailModal);
  document.querySelector('[data-close-modal="true"]').addEventListener('click', closeDetailModal);

  document.getElementById('voice-mute-button').addEventListener('click', () => {
    if (window.voice) {
      window.voice.toggleMute();
    }
  });

  document.querySelectorAll('.persona-card').forEach((card) => {
    card.addEventListener('click', () => {
      const chosen = card.dataset.persona;
      appState.activePersona = chosen;
      renderPersonaSelector();
      renderSuggestedQueries();
      showScreen('chat');
    });
  });

  document.getElementById('chat-input').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      sendQuery(event.target.value, 'typed');
    }
  });
}

window.orcaApp = {
  handleVoiceTranscript(transcript) {
    const input = document.getElementById('chat-input');
    if (!input) return;
    input.value = transcript;
    sendQuery(transcript, 'voice');
  }
};

document.addEventListener('DOMContentLoaded', () => {
  renderPersonaSelector();
  renderSuggestedQueries();
  renderExamples();
  wireEvents();
  showScreen('intro');
});
