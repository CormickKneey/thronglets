import { useCallback } from "react";
import { Card, CardHeader, CardBody, Button, Badge } from "../components";
import { systemApi, type SystemInfo, type McpTool } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import "./SystemPage.css";

export function SystemPage() {
  const fetchSystemInfo = useCallback(() => systemApi.getInfo(), []);
  const { data: systemInfo, isLoading, error, refresh } = usePolling(fetchSystemInfo, { interval: 10000 });

  if (error) {
    return (
      <div className="system-page">
        <div className="system-page__error">
          <p>Failed to load system info: {error.message}</p>
          <Button onClick={refresh}>Retry</Button>
        </div>
      </div>
    );
  }

  if (isLoading && !systemInfo) {
    return (
      <div className="system-page">
        <div className="system-page__loading">Loading system info...</div>
      </div>
    );
  }

  if (!systemInfo) return null;

  return (
    <div className="system-page">
      <div className="system-page__header">
        <h2>System</h2>
        <Button variant="outline" onClick={refresh} disabled={isLoading}>
          {isLoading ? "..." : "Refresh"}
        </Button>
      </div>

      <div className="system-page__grid">
        <AboutSection info={systemInfo} />
        <HealthSection info={systemInfo} />
        <McpSection info={systemInfo} />
        <EndpointsSection info={systemInfo} />
      </div>
    </div>
  );
}

function AboutSection({ info }: { info: SystemInfo }) {
  return (
    <Card>
      <CardHeader>
        <h3>About</h3>
      </CardHeader>
      <CardBody>
        <div className="about-section">
          <div className="about-section__title">
            <h4>{info.name}</h4>
            <Badge variant="primary">v{info.version}</Badge>
          </div>
          <p className="about-section__description">{info.description}</p>
          <div className="about-section__features">
            <h5>Key Features</h5>
            <ul>
              <li>Agent registration and discovery</li>
              <li>Inter-agent messaging via MCP protocol</li>
              <li>Task management and tracking</li>
              <li>App registry with health check monitoring</li>
              <li>A2A (Agent-to-Agent) protocol support</li>
            </ul>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function HealthSection({ info }: { info: SystemInfo }) {
  const { health } = info;
  const isHealthy = health.status === "healthy";
  const now = new Date();

  return (
    <Card variant={isHealthy ? "default" : "primary"}>
      <CardHeader>
        <div className="health-header">
          <h3>Health Status</h3>
          <Badge variant={isHealthy ? "success" : "danger"}>
            {health.status.toUpperCase()}
          </Badge>
        </div>
      </CardHeader>
      <CardBody>
        <div className="health-stats">
          <div className="health-stat">
            <span className="health-stat__value">{health.agents_count}</span>
            <span className="health-stat__label">Agents</span>
          </div>
          <div className="health-stat">
            <span className="health-stat__value">{health.apps_count}</span>
            <span className="health-stat__label">Apps</span>
          </div>
          <div className="health-stat">
            <span className="health-stat__value">{health.healthy_apps_count}</span>
            <span className="health-stat__label">Healthy Apps</span>
          </div>
        </div>
        <div className="health-timestamp">
          <span className="health-timestamp__label">Last Detected At</span>
          <span className="health-timestamp__value">{now.toLocaleString()}</span>
        </div>
      </CardBody>
    </Card>
  );
}

function McpSection({ info }: { info: SystemInfo }) {
  const { mcp } = info;
  const toolsByCategory = mcp.tools.reduce((acc, tool) => {
    if (!acc[tool.category]) {
      acc[tool.category] = [];
    }
    acc[tool.category].push(tool);
    return acc;
  }, {} as Record<string, McpTool[]>);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <Card className="mcp-section">
      <CardHeader>
        <h3>MCP Server</h3>
      </CardHeader>
      <CardBody>
        <div className="mcp-info">
          <div className="mcp-endpoint">
            <strong>Endpoint:</strong>
            <div className="mcp-endpoint__url">
              <code>{mcp.endpoint}</code>
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(mcp.endpoint)}
              >
                Copy
              </Button>
            </div>
          </div>
          <div className="mcp-transport">
            <strong>Transport:</strong>
            <Badge variant="default">{mcp.transport}</Badge>
          </div>

          <div className="mcp-tools">
            <h4>Available Tools ({mcp.tools.length})</h4>
            {Object.entries(toolsByCategory).map(([category, tools]) => (
              <div key={category} className="mcp-tools__category">
                <h5>{category}</h5>
                <div className="mcp-tools__list">
                  {tools.map((tool) => (
                    <div key={tool.name} className="mcp-tool">
                      <code className="mcp-tool__name">{tool.name}</code>
                      <span className="mcp-tool__description">{tool.description}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function EndpointsSection({ info }: { info: SystemInfo }) {
  const { endpoints } = info;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <Card>
      <CardHeader>
        <h3>API Endpoints</h3>
      </CardHeader>
      <CardBody>
        <div className="endpoints-list">
          <div className="endpoint-item">
            <strong>Base URL</strong>
            <div className="endpoint-item__url">
              <code>{endpoints.base_url}</code>
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(endpoints.base_url)}
              >
                Copy
              </Button>
            </div>
          </div>
          <div className="endpoint-item">
            <strong>MCP URL</strong>
            <div className="endpoint-item__url">
              <code>{endpoints.mcp_url}</code>
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(endpoints.mcp_url)}
              >
                Copy
              </Button>
            </div>
          </div>
          <div className="endpoint-item">
            <strong>Agent Card</strong>
            <div className="endpoint-item__url">
              <code>{endpoints.agent_card}</code>
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(endpoints.agent_card)}
              >
                Copy
              </Button>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
