import ChatWidget from "./ChatWidget";

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <h2>Customer Service Agent</h2>
        <p>
          This is your AI-powered support assistant. Customize your business
          details in <code>config/business.yaml</code> to train it on your
          products, policies, and FAQs.
        </p>
        <ul>
          <li>Answers common questions instantly</li>
          <li>Looks up hours, products, and policies</li>
          <li>Escalates to your team when needed</li>
        </ul>
      </aside>
      <main>
        <ChatWidget />
      </main>
    </div>
  );
}
