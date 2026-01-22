import { useState } from "react";
import { Tabs, TabPanel } from "./components";
import { AppsPage, AgentsPage, TasksPage, SystemPage } from "./pages";
import "./App.css";

const tabs = [
  { id: "apps", label: "Apps" },
  { id: "agents", label: "Agents" },
  { id: "tasks", label: "Tasks" },
  { id: "system", label: "System" },
];

function App() {
  const [activeTab, setActiveTab] = useState("apps");

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">Thronglets</h1>
        <span className="app__subtitle">Multi-Agent ServiceBus</span>
      </header>

      <main className="app__main">
        <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

        <TabPanel id="apps" activeTab={activeTab}>
          <AppsPage />
        </TabPanel>

        <TabPanel id="agents" activeTab={activeTab}>
          <AgentsPage />
        </TabPanel>

        <TabPanel id="tasks" activeTab={activeTab}>
          <TasksPage />
        </TabPanel>

        <TabPanel id="system" activeTab={activeTab}>
          <SystemPage />
        </TabPanel>
      </main>

      <footer className="app__footer">
        <span>Thronglets ServiceBus Dashboard</span>
      </footer>
    </div>
  );
}

export default App;
