import { useState, useCallback } from "react";
import {
  Card,
  CardHeader,
  CardBody,
  Button,
  Modal,
  Badge,
} from "../components";
import { agentApi } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import type { RegisteredAgent, AgentSkill, AgentCapabilities } from "../types";
import "./AgentsPage.css";

export function AgentsPage() {
  const [selectedAgent, setSelectedAgent] = useState<RegisteredAgent | null>(null);

  const fetchAgents = useCallback(() => agentApi.list(), []);
  const { data: agentsResponse, isLoading, error, refresh } = usePolling(fetchAgents);
  const agents = agentsResponse?.agents;

  if (error) {
    return (
      <div className="agents-page">
        <div className="agents-page__error">
          <p>Failed to load agents: {error.message}</p>
          <Button onClick={refresh}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="agents-page">
      <div className="agents-page__header">
        <h2>Agents</h2>
        <Button variant="outline" onClick={refresh} disabled={isLoading}>
          {isLoading ? "..." : "Refresh"}
        </Button>
      </div>

      {isLoading && !agents ? (
        <div className="agents-page__loading">Loading agents...</div>
      ) : agents?.length === 0 ? (
        <div className="agents-page__empty">
          <p>No agents registered yet.</p>
          <p>Agents will appear here when they connect to the ServiceBus.</p>
        </div>
      ) : (
        <div className="agents-grid">
          {agents?.map((agent) => (
            <AgentCardComponent
              key={agent.agent_id}
              agent={agent}
              onView={() => setSelectedAgent(agent)}
            />
          ))}
        </div>
      )}

      <AgentDetailModal
        agent={selectedAgent}
        onClose={() => setSelectedAgent(null)}
      />
    </div>
  );
}

interface AgentCardComponentProps {
  agent: RegisteredAgent;
  onView: () => void;
}

function AgentCardComponent({ agent, onView }: AgentCardComponentProps) {
  const { card } = agent;

  return (
    <Card onClick={onView}>
      <CardHeader>
        <div className="agent-card__header">
          <div className="agent-card__title">
            {card.icon_url && (
              <img
                src={card.icon_url}
                alt=""
                className="agent-card__icon"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            )}
            <h4>{card.name}</h4>
          </div>
          <Badge variant="primary" size="sm">
            v{card.version}
          </Badge>
        </div>
      </CardHeader>
      <CardBody>
        <p className="agent-card__description">{card.description}</p>
        {card.skills && card.skills.length > 0 && (
          <div className="agent-card__skills">
            <strong>Skills ({card.skills.length}):</strong>
            <div className="agent-card__skill-tags">
              {card.skills.slice(0, 3).map((skill) => (
                <Badge key={skill.id} variant="default" size="sm">
                  {skill.name}
                </Badge>
              ))}
              {card.skills.length > 3 && (
                <Badge variant="default" size="sm">
                  +{card.skills.length - 3} more
                </Badge>
              )}
            </div>
          </div>
        )}
        <div className="agent-card__meta">
          <span className="agent-card__last-seen">
            Last seen: {formatRelativeTime(new Date(agent.last_seen_at))}
          </span>
        </div>
      </CardBody>
    </Card>
  );
}

interface AgentDetailModalProps {
  agent: RegisteredAgent | null;
  onClose: () => void;
}

function AgentDetailModal({ agent, onClose }: AgentDetailModalProps) {
  const [activeSection, setActiveSection] = useState<"info" | "skills" | "capabilities">("info");

  if (!agent) return null;

  const { card } = agent;

  return (
    <Modal isOpen={!!agent} onClose={onClose} title={card.name}>
      <div className="agent-detail">
        <div className="agent-detail__tabs">
          <button
            className={`agent-detail__tab ${activeSection === "info" ? "active" : ""}`}
            onClick={() => setActiveSection("info")}
          >
            Info
          </button>
          <button
            className={`agent-detail__tab ${activeSection === "skills" ? "active" : ""}`}
            onClick={() => setActiveSection("skills")}
          >
            Skills ({card.skills?.length || 0})
          </button>
          <button
            className={`agent-detail__tab ${activeSection === "capabilities" ? "active" : ""}`}
            onClick={() => setActiveSection("capabilities")}
          >
            Capabilities
          </button>
        </div>

        {activeSection === "info" && (
          <div className="agent-detail__section">
            <div className="agent-detail__row">
              <strong>Version:</strong>
              <Badge variant="primary">{card.version}</Badge>
            </div>
            <div className="agent-detail__row">
              <strong>Description:</strong>
              <p>{card.description}</p>
            </div>
            {card.provider && (
              <div className="agent-detail__row">
                <strong>Provider:</strong>
                <span>
                  {card.provider.name}
                  {card.provider.url && (
                    <a
                      href={card.provider.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="agent-detail__link"
                    >
                      {" "}(Link)
                    </a>
                  )}
                </span>
              </div>
            )}
            {card.supported_interfaces && card.supported_interfaces.length > 0 && (
              <div className="agent-detail__row">
                <strong>Interfaces:</strong>
                <div className="agent-detail__interfaces">
                  {card.supported_interfaces.map((iface, idx) => (
                    <div key={idx} className="agent-detail__interface">
                      <code>{iface.url}</code>
                      <Badge variant="default" size="sm">
                        {iface.protocol_binding}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="agent-detail__row">
              <strong>Registered:</strong>
              <span>{new Date(agent.registered_at).toLocaleString()}</span>
            </div>
            <div className="agent-detail__row">
              <strong>Last Seen:</strong>
              <span>{new Date(agent.last_seen_at).toLocaleString()}</span>
            </div>
            <div className="agent-detail__row">
              <strong>Agent ID:</strong>
              <code>{agent.agent_id}</code>
            </div>
          </div>
        )}

        {activeSection === "skills" && (
          <div className="agent-detail__section">
            <SkillsList skills={card.skills || []} />
          </div>
        )}

        {activeSection === "capabilities" && (
          <div className="agent-detail__section">
            <CapabilitiesView capabilities={card.capabilities} />
            {card.default_input_modes && (
              <div className="agent-detail__row">
                <strong>Input Modes:</strong>
                <div className="agent-detail__modes">
                  {card.default_input_modes.map((mode) => (
                    <Badge key={mode} variant="default" size="sm">
                      {mode}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {card.default_output_modes && (
              <div className="agent-detail__row">
                <strong>Output Modes:</strong>
                <div className="agent-detail__modes">
                  {card.default_output_modes.map((mode) => (
                    <Badge key={mode} variant="default" size="sm">
                      {mode}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

function SkillsList({ skills }: { skills: AgentSkill[] }) {
  if (skills.length === 0) {
    return <p className="agent-detail__empty">No skills defined.</p>;
  }

  return (
    <div className="skills-list">
      {skills.map((skill) => (
        <div key={skill.id} className="skill-item">
          <div className="skill-item__header">
            <h5>{skill.name}</h5>
            <code className="skill-item__id">{skill.id}</code>
          </div>
          <p className="skill-item__description">{skill.description}</p>
          {skill.tags && skill.tags.length > 0 && (
            <div className="skill-item__tags">
              {skill.tags.map((tag) => (
                <Badge key={tag} variant="default" size="sm">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function CapabilitiesView({ capabilities }: { capabilities?: AgentCapabilities }) {
  if (!capabilities) {
    return <p className="agent-detail__empty">No capabilities defined.</p>;
  }

  const items = [
    { key: "streaming", label: "Streaming", value: capabilities.streaming },
    {
      key: "push_notifications",
      label: "Push Notifications",
      value: capabilities.push_notifications,
    },
    {
      key: "state_transition_history",
      label: "State Transition History",
      value: capabilities.state_transition_history,
    },
  ];

  return (
    <div className="capabilities-list">
      {items.map((item) => (
        <div key={item.key} className="capability-item">
          <span className="capability-item__label">{item.label}</span>
          <Badge variant={item.value ? "success" : "default"} size="sm">
            {item.value ? "Yes" : "No"}
          </Badge>
        </div>
      ))}
    </div>
  );
}

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return "just now";
}
