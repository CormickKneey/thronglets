import { useState, useCallback, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  Button,
  Modal,
  Badge,
  Input,
  Textarea,
} from "../components";
import { appApi } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import type { RegisteredApp, AppCard, ToolInfo } from "../types";
import "./AppsPage.css";

export function AppsPage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedApp, setSelectedApp] = useState<RegisteredApp | null>(null);
  const [editingApp, setEditingApp] = useState<RegisteredApp | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchApps = useCallback(() => appApi.list(), []);
  const { data: appsResponse, isLoading, error, refresh } = usePolling(fetchApps);
  const apps = appsResponse?.apps;

  const handleCreateApp = async (card: AppCard) => {
    await appApi.create(card);
    setIsCreateModalOpen(false);
    refresh();
  };

  const handleUpdateApp = async (appId: string, card: AppCard) => {
    await appApi.update(appId, card);
    setEditingApp(null);
    refresh();
  };

  const handleDeleteApp = async (appId: string) => {
    await appApi.delete(appId);
    setDeleteConfirm(null);
    refresh();
  };

  if (error) {
    return (
      <div className="apps-page">
        <div className="apps-page__error">
          <p>Failed to load apps: {error.message}</p>
          <Button onClick={refresh}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="apps-page">
      <div className="apps-page__header">
        <h2>Apps</h2>
        <div className="apps-page__actions">
          <Button variant="outline" onClick={refresh} disabled={isLoading}>
            {isLoading ? "..." : "Refresh"}
          </Button>
          <Button variant="primary" onClick={() => setIsCreateModalOpen(true)}>
            + Add App
          </Button>
        </div>
      </div>

      {isLoading && !apps ? (
        <div className="apps-page__loading">Loading apps...</div>
      ) : apps?.length === 0 ? (
        <div className="apps-page__empty">
          <p>No apps registered yet.</p>
          <Button variant="primary" onClick={() => setIsCreateModalOpen(true)}>
            Register your first app
          </Button>
        </div>
      ) : (
        <div className="apps-grid">
          {apps?.map((app) => (
            <AppCardComponent
              key={app.app_id}
              app={app}
              onView={() => setSelectedApp(app)}
              onEdit={() => setEditingApp(app)}
              onDelete={() => setDeleteConfirm(app.app_id)}
            />
          ))}
        </div>
      )}

      <AppFormModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateApp}
        title="Register New App"
        submitLabel="Create App"
      />

      <AppFormModal
        isOpen={!!editingApp}
        onClose={() => setEditingApp(null)}
        onSubmit={(card) => editingApp ? handleUpdateApp(editingApp.app_id, card) : Promise.resolve()}
        title="Edit App"
        submitLabel="Save Changes"
        initialData={editingApp?.card}
      />

      <AppDetailModal
        app={selectedApp}
        onClose={() => setSelectedApp(null)}
      />

      <Modal
        isOpen={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        title="Delete App"
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => deleteConfirm && handleDeleteApp(deleteConfirm)}
            >
              Delete
            </Button>
          </>
        }
      >
        <p>Are you sure you want to delete this app? This action cannot be undone.</p>
      </Modal>
    </div>
  );
}

interface AppCardComponentProps {
  app: RegisteredApp;
  onView: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

function AppCardComponent({ app, onView, onEdit, onDelete }: AppCardComponentProps) {
  return (
    <Card>
      <CardHeader>
        <div className="app-card__header">
          <h4>{app.card.name}</h4>
          <Badge variant={app.healthy ? "success" : "danger"} size="sm">
            {app.healthy ? "Healthy" : "Unhealthy"}
          </Badge>
        </div>
      </CardHeader>
      <CardBody>
        <p className="app-card__description">{app.card.description}</p>
        <div className="app-card__meta">
          <span className="app-card__scenario">
            <strong>Scenario:</strong> {app.card.scenario}
          </span>
          {app.card.tags && app.card.tags.length > 0 && (
            <div className="app-card__tags">
              {app.card.tags.map((tag) => (
                <Badge key={tag} variant="default" size="sm">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </CardBody>
      <CardFooter>
        <Button variant="outline" size="sm" onClick={onView}>
          View
        </Button>
        <Button variant="primary" size="sm" onClick={onEdit}>
          Edit
        </Button>
        <Button variant="danger" size="sm" onClick={onDelete}>
          Delete
        </Button>
      </CardFooter>
    </Card>
  );
}

interface AppFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (card: AppCard) => Promise<void>;
  title: string;
  submitLabel: string;
  initialData?: AppCard;
}

function AppFormModal({ isOpen, onClose, onSubmit, title, submitLabel, initialData }: AppFormModalProps) {
  const [formData, setFormData] = useState<AppCard>({
    name: "",
    description: "",
    scenario: "",
    mcp_endpoint: "",
    health_check_url: "",
    tags: [],
  });
  const [tagsInput, setTagsInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setFormData(initialData);
      setTagsInput(initialData.tags?.join(", ") || "");
    } else {
      setFormData({
        name: "",
        description: "",
        scenario: "",
        mcp_endpoint: "",
        health_check_url: "",
        tags: [],
      });
      setTagsInput("");
    }
    setError(null);
  }, [initialData, isOpen]);

  const handleSubmit = async () => {
    if (!formData.name || !formData.description || !formData.scenario || !formData.mcp_endpoint || !formData.health_check_url) {
      setError("All fields are required");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const tags = tagsInput
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await onSubmit({ ...formData, tags });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operation failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? "..." : submitLabel}
          </Button>
        </>
      }
    >
      <div className="create-app-form">
        {error && <div className="form-error">{error}</div>}
        <Input
          label="Name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="My App"
        />
        <Textarea
          label="Description"
          value={formData.description}
          onChange={(e) =>
            setFormData({ ...formData, description: e.target.value })
          }
          placeholder="What does this app do?"
        />
        <Input
          label="Scenario"
          value={formData.scenario}
          onChange={(e) =>
            setFormData({ ...formData, scenario: e.target.value })
          }
          placeholder="e.g., finance, game-dev, data-analysis"
        />
        <Input
          label="MCP Endpoint"
          value={formData.mcp_endpoint}
          onChange={(e) =>
            setFormData({ ...formData, mcp_endpoint: e.target.value })
          }
          placeholder="http://localhost:8000/mcp"
        />
        <Input
          label="Health Check URL"
          value={formData.health_check_url}
          onChange={(e) =>
            setFormData({ ...formData, health_check_url: e.target.value })
          }
          placeholder="http://localhost:8000/health"
        />
        <Input
          label="Tags (comma separated)"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          placeholder="tag1, tag2, tag3"
        />
      </div>
    </Modal>
  );
}

interface AppDetailModalProps {
  app: RegisteredApp | null;
  onClose: () => void;
}

function AppDetailModal({ app, onClose }: AppDetailModalProps) {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState<string | null>(null);
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (app && app.healthy) {
      setToolsLoading(true);
      setToolsError(null);
      appApi
        .getTools(app.app_id)
        .then((response) => {
          setTools(response.tools);
        })
        .catch((err) => {
          setToolsError(err.message || "Failed to load tools");
        })
        .finally(() => {
          setToolsLoading(false);
        });
    } else {
      setTools([]);
      setToolsError(null);
    }
  }, [app]);

  const toggleToolExpand = (toolName: string) => {
    setExpandedTools((prev) => {
      const next = new Set(prev);
      if (next.has(toolName)) {
        next.delete(toolName);
      } else {
        next.add(toolName);
      }
      return next;
    });
  };

  if (!app) return null;

  return (
    <Modal isOpen={!!app} onClose={onClose} title={app.card.name}>
      <div className="app-detail">
        <div className="app-detail__row">
          <strong>Status:</strong>
          <Badge variant={app.healthy ? "success" : "danger"}>
            {app.healthy ? "Healthy" : "Unhealthy"}
          </Badge>
        </div>
        <div className="app-detail__row">
          <strong>Description:</strong>
          <p>{app.card.description}</p>
        </div>
        <div className="app-detail__row">
          <strong>Scenario:</strong>
          <span>{app.card.scenario}</span>
        </div>
        <div className="app-detail__row">
          <strong>MCP Endpoint:</strong>
          <code>{app.card.mcp_endpoint}</code>
        </div>
        <div className="app-detail__row">
          <strong>Health Check URL:</strong>
          <code>{app.card.health_check_url}</code>
        </div>
        {app.card.tags && app.card.tags.length > 0 && (
          <div className="app-detail__row">
            <strong>Tags:</strong>
            <div className="app-detail__tags">
              {app.card.tags.map((tag) => (
                <Badge key={tag} variant="default" size="sm">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}
        <div className="app-detail__row">
          <strong>Registered:</strong>
          <span>{new Date(app.registered_at).toLocaleString()}</span>
        </div>
        <div className="app-detail__row">
          <strong>Last Seen:</strong>
          <span>{new Date(app.last_seen_at).toLocaleString()}</span>
        </div>
        <div className="app-detail__row">
          <strong>App ID:</strong>
          <code>{app.app_id}</code>
        </div>

        {/* Tools Section */}
        <div className="app-detail__tools-section">
          <h4>MCP Tools</h4>
          {toolsLoading ? (
            <div className="app-detail__tools-loading">Loading tools...</div>
          ) : toolsError ? (
            <div className="app-detail__tools-error">{toolsError}</div>
          ) : !app.healthy ? (
            <div className="app-detail__tools-unavailable">
              Tools unavailable (app is not healthy)
            </div>
          ) : tools.length === 0 ? (
            <div className="app-detail__tools-empty">No tools available</div>
          ) : (
            <div className="app-detail__tools-list">
              {tools.map((tool) => (
                <div key={tool.name} className="tool-card">
                  <div
                    className="tool-card__header"
                    onClick={() => toggleToolExpand(tool.name)}
                  >
                    <span className="tool-card__name">{tool.name}</span>
                    <span className="tool-card__expand">
                      {expandedTools.has(tool.name) ? "▼" : "▶"}
                    </span>
                  </div>
                  <p className="tool-card__description">{tool.description}</p>
                  {expandedTools.has(tool.name) && (
                    <div className="tool-card__schema">
                      <strong>Input Schema:</strong>
                      <pre>{JSON.stringify(tool.inputSchema, null, 2)}</pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
