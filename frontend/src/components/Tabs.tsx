import type { ReactNode } from "react";
import "./Tabs.css";

interface Tab {
  id: string;
  label: string;
  icon?: ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export function Tabs({ tabs, activeTab, onTabChange }: TabsProps) {
  return (
    <div className="brutal-tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`brutal-tab ${activeTab === tab.id ? "brutal-tab--active" : ""}`}
          onClick={() => onTabChange(tab.id)}
          role="tab"
          aria-selected={activeTab === tab.id}
          aria-controls={`tabpanel-${tab.id}`}
        >
          {tab.icon && <span className="brutal-tab__icon">{tab.icon}</span>}
          {tab.label}
        </button>
      ))}
    </div>
  );
}

interface TabPanelProps {
  id: string;
  activeTab: string;
  children: ReactNode;
}

export function TabPanel({ id, activeTab, children }: TabPanelProps) {
  if (activeTab !== id) return null;

  return (
    <div
      id={`tabpanel-${id}`}
      role="tabpanel"
      aria-labelledby={id}
      className="brutal-tabpanel"
    >
      {children}
    </div>
  );
}
