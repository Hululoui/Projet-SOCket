import { useEffect, useMemo, useState } from "react";
import "./App.css";

function App() {
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [severityFilter, setSeverityFilter] = useState("ALL");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const statsResponse = await fetch("http://localhost:3000/api/stats");
        const alertsResponse = await fetch("http://localhost:3000/api/alerts");

        if (!statsResponse.ok) {
          throw new Error(`Stats API error: ${statsResponse.status}`);
        }

        if (!alertsResponse.ok) {
          throw new Error(`Alerts API error: ${alertsResponse.status}`);
        }

        const statsData = await statsResponse.json();
        const alertsData = await alertsResponse.json();

        setStats(statsData);
        setAlerts(alertsData);
      } catch (err) {
        console.error("Erreur fetch dashboard :", err);
        setError(err.message || "Impossible de récupérer les données du dashboard.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const filteredAlerts = useMemo(() => {
    if (severityFilter === "ALL") {
      return alerts;
    }

    return alerts.filter((alert) => alert.severity === severityFilter);
  }, [alerts, severityFilter]);

  if (loading) {
    return <div className="app-message">Chargement du dashboard...</div>;
  }

  if (error) {
    return <div className="app-message error">{error}</div>;
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>SOCket Dashboard</h1>
        <p>Vue d’ensemble des alertes et incidents de sécurité.</p>
      </header>

      <section className="stats-grid">
        <div className="stat-card">
          <h2>Total alertes</h2>
          <p>{stats.totalAlerts}</p>
        </div>

        <div className="stat-card">
          <h2>Alertes critiques</h2>
          <p>{stats.criticalAlerts}</p>
        </div>

        <div className="stat-card">
          <h2>Incidents ouverts</h2>
          <p>{stats.openIncidents}</p>
        </div>

        <div className="stat-card">
          <h2>Sources de données</h2>
          <p>{stats.dataSources}</p>
        </div>

        <div className="stat-card">
          <h2>Alertes 24h</h2>
          <p>{stats.last24hAlerts}</p>
        </div>
      </section>

      <section className="alerts-section">
        <div className="alerts-header">
          <h2>Alertes récentes</h2>

          <select
            className="severity-filter"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="ALL">Toutes les sévérités</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        <div className="alerts-list">
          {filteredAlerts.map((alert) => (
            <article className="alert-card" key={alert.id}>
              <div className="alert-top">
                <span className={`badge severity ${alert.severity.toLowerCase()}`}>
                  {alert.severity}
                </span>
                <span className="badge status">{alert.status}</span>
              </div>

              <h3>{alert.title}</h3>
              <p className="alert-description">{alert.description}</p>

              <ul className="alert-meta">
                <li><strong>ID :</strong> {alert.id}</li>
                <li><strong>Source :</strong> {alert.source}</li>
                <li><strong>Asset :</strong> {alert.asset}</li>
                <li><strong>First seen :</strong> {alert.firstSeen}</li>
                <li><strong>Last seen :</strong> {alert.lastSeen}</li>
              </ul>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

export default App;