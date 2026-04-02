const express = require("express");
const cors = require("cors");
const fs = require("fs/promises");
const path = require("path");

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

const dataPath = (fileName) => path.join(__dirname, "data", fileName);

app.get("/api/stats", async (req, res) => {
  try {
    const stats = await fs.readFile(dataPath("stats.json"), "utf-8");
    res.json(JSON.parse(stats));
  } catch (error) {
    res.status(500).json({ error: "Impossible de charger les statistiques." });
  }
});

app.get("/api/alerts", async (req, res) => {
  try {
    const alerts = await fs.readFile(dataPath("alerts.json"), "utf-8");
    res.json(JSON.parse(alerts));
  } catch (error) {
    res.status(500).json({ error: "Impossible de charger les alertes." });
  }
});

app.get("/", (req, res) => {
  res.json({ message: "API SOCket opérationnelle" });
});

app.listen(PORT, () => {
  console.log(`Serveur backend démarré sur http://localhost:${PORT}`);
});