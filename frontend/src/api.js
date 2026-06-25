const API_BASE = import.meta.env.VITE_API_URL || "";

export async function fetchBusinessInfo() {
  const response = await fetch(`${API_BASE}/api/business`);
  if (!response.ok) {
    throw new Error("Failed to load business info");
  }
  return response.json();
}

export async function sendMessage({ message, conversationId, history }) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      history,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to send message");
  }

  return response.json();
}
