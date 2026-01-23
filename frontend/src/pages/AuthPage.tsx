import { useState, useCallback } from "react";
import { Card, CardHeader, CardBody, Button, Badge, Modal, Input, CopyButton } from "../components";
import { systemApi, type SystemInfo } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import { copyToClipboard } from "../utils/clipboard";
import "./AuthPage.css";

export function AuthPage() {
  const fetchSystemInfo = useCallback(() => systemApi.getInfo(), []);
  const { data: systemInfo, isLoading, error, refresh } = usePolling(fetchSystemInfo, { interval: 10000 });

  if (error) {
    return (
      <div className="auth-page">
        <div className="auth-page__error">
          <p>Failed to load auth info: {error.message}</p>
          <Button onClick={refresh}>Retry</Button>
        </div>
      </div>
    );
  }

  if (isLoading && !systemInfo) {
    return (
      <div className="auth-page">
        <div className="auth-page__loading">Loading auth info...</div>
      </div>
    );
  }

  if (!systemInfo) return null;

  const authConfig = systemInfo.mcp.auth;

  return (
    <div className="auth-page">
      <div className="auth-page__header">
        <h2>Authentication</h2>
        <Button variant="outline" onClick={refresh} disabled={isLoading}>
          {isLoading ? "..." : "Refresh"}
        </Button>
      </div>

      <div className="auth-page__grid">
        <AuthStatusSection authConfig={authConfig} />
        {authConfig.enabled && authConfig.supabase_url && authConfig.supabase_anon_key && (
          <GetTokenSection
            supabaseUrl={authConfig.supabase_url}
            supabaseAnonKey={authConfig.supabase_anon_key}
          />
        )}
        <UsageGuideSection authConfig={authConfig} mcpEndpoint={systemInfo.mcp.endpoint} />
      </div>
    </div>
  );
}

function AuthStatusSection({ authConfig }: { authConfig: SystemInfo["mcp"]["auth"] }) {
  return (
    <Card>
      <CardHeader>
        <div className="auth-status-header">
          <h3>Auth Status</h3>
          <Badge variant={authConfig.enabled ? "success" : "default"}>
            {authConfig.enabled ? "ENABLED" : "DISABLED"}
          </Badge>
        </div>
      </CardHeader>
      <CardBody>
        <div className="auth-status">
          {authConfig.enabled ? (
            <>
              <p className="auth-status__description">
                JWT authentication is enabled. You need a valid Supabase access token to call MCP tools.
              </p>
              <div className="auth-status__config">
                <div className="auth-status__item">
                  <strong>Supabase URL</strong>
                  <code>{authConfig.supabase_url || "Not configured"}</code>
                </div>
                <div className="auth-status__item">
                  <strong>Anon Key</strong>
                  <code>{authConfig.supabase_anon_key ? "Configured" : "Not configured"}</code>
                </div>
              </div>
            </>
          ) : (
            <p className="auth-status__description">
              Authentication is disabled. MCP tools can be called without a token.
            </p>
          )}
        </div>
      </CardBody>
    </Card>
  );
}

interface GetTokenSectionProps {
  supabaseUrl: string;
  supabaseAnonKey: string;
}

function GetTokenSection({ supabaseUrl, supabaseAnonKey }: GetTokenSectionProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [copyStatus, setCopyStatus] = useState<{ token?: boolean; header?: boolean }>({});

  const handleGetToken = async () => {
    if (!email || !password) {
      setError("Please enter both email and password");
      return;
    }

    setIsLoading(true);
    setError("");
    setAccessToken("");

    try {
      const response = await fetch(`${supabaseUrl}/auth/v1/token?grant_type=password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "apikey": supabaseAnonKey,
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error_description || data.msg || "Failed to get token");
      }

      setAccessToken(data.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get token");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyToken = async () => {
    const success = await copyToClipboard(accessToken);
    if (success) {
      setCopyStatus({ token: true });
      setTimeout(() => setCopyStatus({}), 2000);
    }
  };

  const handleCopyHeader = async () => {
    const success = await copyToClipboard(`Authorization: Bearer ${accessToken}`);
    if (success) {
      setCopyStatus({ header: true });
      setTimeout(() => setCopyStatus({}), 2000);
    }
  };

  return (
    <>
      <Card variant="primary">
        <CardHeader>
          <h3>Get Access Token</h3>
        </CardHeader>
        <CardBody>
          <div className="get-token">
            <p className="get-token__description">
              Sign in with your Supabase account to get an access token for MCP authentication.
            </p>
            <Button onClick={() => setIsModalOpen(true)}>Get Token</Button>
          </div>
        </CardBody>
      </Card>

      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setError("");
          setAccessToken("");
        }}
        title="Get Supabase Access Token"
        footer={
          !accessToken && (
            <div className="modal-footer">
              <Button variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleGetToken} disabled={isLoading}>
                {isLoading ? "Signing in..." : "Sign In"}
              </Button>
            </div>
          )
        }
      >
        {!accessToken ? (
          <div className="token-form">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
            />
            {error && <div className="token-form__error">{error}</div>}
          </div>
        ) : (
          <div className="token-result">
            <div className="token-result__success">
              <Badge variant="success">Success</Badge>
              <span>Token generated successfully!</span>
            </div>

            <div className="token-result__section">
              <strong>Access Token</strong>
              <div className="token-result__value">
                <code>{accessToken.slice(0, 50)}...</code>
                <Button variant="outline" size="sm" onClick={handleCopyToken}>
                  {copyStatus.token ? "Copied!" : "Copy"}
                </Button>
              </div>
            </div>

            <div className="token-result__section">
              <strong>Authorization Header</strong>
              <div className="token-result__value">
                <code>Authorization: Bearer {accessToken.slice(0, 20)}...</code>
                <Button variant="outline" size="sm" onClick={handleCopyHeader}>
                  {copyStatus.header ? "Copied!" : "Copy"}
                </Button>
              </div>
            </div>

            <div className="token-result__tip">
              <strong>Next Step:</strong> Add this header to your MCP client configuration.
            </div>

            <Button onClick={() => setIsModalOpen(false)}>Done</Button>
          </div>
        )}
      </Modal>
    </>
  );
}

interface UsageGuideSectionProps {
  authConfig: SystemInfo["mcp"]["auth"];
  mcpEndpoint: string;
}

function UsageGuideSection({ authConfig, mcpEndpoint }: UsageGuideSectionProps) {
  const inspectorConfig = JSON.stringify(
    {
      url: mcpEndpoint,
      headers: {
        Authorization: "Bearer YOUR_ACCESS_TOKEN",
      },
    },
    null,
    2
  );

  return (
    <Card className="usage-guide-section">
      <CardHeader>
        <h3>Usage Guide</h3>
      </CardHeader>
      <CardBody>
        <div className="usage-guide">
          {authConfig.enabled ? (
            <>
              <div className="usage-guide__step">
                <div className="usage-guide__step-number">1</div>
                <div className="usage-guide__step-content">
                  <h4>Get Access Token</h4>
                  <p>Click "Get Token" button above and sign in with your Supabase credentials.</p>
                </div>
              </div>

              <div className="usage-guide__step">
                <div className="usage-guide__step-number">2</div>
                <div className="usage-guide__step-content">
                  <h4>Configure MCP Client</h4>
                  <p>Add the Authorization header to your MCP client configuration:</p>
                  <div className="usage-guide__code">
                    <code>Authorization: Bearer YOUR_ACCESS_TOKEN</code>
                    <CopyButton text="Authorization: Bearer YOUR_ACCESS_TOKEN" />
                  </div>
                </div>
              </div>

              <div className="usage-guide__step">
                <div className="usage-guide__step-number">3</div>
                <div className="usage-guide__step-content">
                  <h4>MCP Inspector Example</h4>
                  <p>In MCP Inspector, add custom headers:</p>
                  <div className="usage-guide__config">
                    <pre>{inspectorConfig}</pre>
                    <CopyButton text={inspectorConfig} />
                  </div>
                </div>
              </div>

              <div className="usage-guide__note">
                <strong>Note:</strong> Access tokens expire after some time. Get a new token when the old one expires.
              </div>
            </>
          ) : (
            <div className="usage-guide__disabled">
              <p>Authentication is currently disabled. You can call MCP tools directly without a token.</p>
              <div className="usage-guide__code">
                <code>{mcpEndpoint}</code>
                <CopyButton text={mcpEndpoint} />
              </div>
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  );
}
