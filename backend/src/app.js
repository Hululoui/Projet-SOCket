const express = require("express");
const cors = require("cors");

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

let messages = [
  { id: 1, text: "Premier message" },
  { id: 2, text: "Deuxième message" }
];

app.get("/api/messages", (req, res) => {
  res.json(messages);
});

app.post("/api/messages", (req, res) => {
  const { text } = req.body;

  if (!text || typeof text !== "string") {
    return res.status(400).json({ error: "Le champ text est obligatoire" });
  }

  const newMessage = {
    id: messages.length + 1,
    text
  };

  messages.push(newMessage);
  res.status(201).json(newMessage);
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});