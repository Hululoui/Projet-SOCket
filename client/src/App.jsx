import { useEffect, useState } from "react";


function App() {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");


  useEffect(() => {
    fetch("http://localhost:3000/api/messages")
      .then((res) => res.json())
      .then((data) => setMessages(data))
      .catch((err) => console.error("Erreur GET :", err));
  }, []);


  const handleSubmit = async (e) => {
    e.preventDefault();


    if (!text.trim()) return;


    try {
      const response = await fetch("http://localhost:3000/api/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ text })
      });


      const newMessage = await response.json();
      setMessages((prev) => [...prev, newMessage]);
      setText("");
    } catch (err) {
      console.error("Erreur POST :", err);
    }
  };


  return (
    <div style={{ padding: "20px" }}>
      <h1>Messages</h1>


      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Écris un message"
        />
        <button type="submit">Envoyer</button>
      </form>


      <ul>
        {messages.map((message) => (
          <li key={message.id}>{message.text}</li>
        ))}
      </ul>
    </div>
  );
}


export default App;