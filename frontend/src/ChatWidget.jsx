import { useEffect, useRef, useState } from "react";
import { fetchBusinessInfo, sendMessage } from "./api";

export default function ChatWidget() {
  const [business, setBusiness] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchBusinessInfo()
      .then((info) => {
        setBusiness(info);
        setMessages([{ role: "assistant", content: info.greeting }]);
      })
      .catch(() => setError("Unable to connect to the customer service agent."));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMessage = { role: "user", content: trimmed };
    const history = messages.filter((msg) => msg.role !== "system");

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await sendMessage({
        message: trimmed,
        conversationId,
        history,
      });

      setConversationId(response.conversation_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.reply },
      ]);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-widget">
      <header className="chat-header">
        <div className="avatar">CS</div>
        <div>
          <h1>{business?.name || "Customer Service"}</h1>
          <p>Online · Typically replies instantly</p>
        </div>
      </header>

      <div className="chat-messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="bubble">{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="bubble typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
        {error && <p className="error">{error}</p>}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Type your message..."
          disabled={loading || !business}
          aria-label="Message"
        />
        <button type="submit" disabled={loading || !input.trim() || !business}>
          Send
        </button>
      </form>
    </div>
  );
}
