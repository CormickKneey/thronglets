import { useState, useCallback } from "react";
import {
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  Button,
  Modal,
  Badge,
} from "../components";
import { taskApi } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import type { Task, Message, Part, TaskStateType } from "../types";
import "./TasksPage.css";

export function TasksPage() {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [taskDetail, setTaskDetail] = useState<Task | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchTasks = useCallback(() => taskApi.list({ page_size: 50 }), []);
  const { data: tasksResponse, isLoading, error, refresh } = usePolling(fetchTasks);

  const handleViewTask = async (task: Task) => {
    setSelectedTask(task);
    setIsLoadingDetail(true);
    try {
      const detail = await taskApi.get(task.id, 100);
      setTaskDetail(detail);
    } catch {
      setTaskDetail(null);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedTask(null);
    setTaskDetail(null);
  };

  const handleDeleteTask = async (taskId: string) => {
    await taskApi.delete(taskId);
    setDeleteConfirm(null);
    refresh();
  };

  // Safely extract tasks array with fallback
  const tasks = tasksResponse?.tasks ?? [];

  // Debug log for development
  if (import.meta.env.DEV) {
    console.log("[TasksPage] state:", { isLoading, error: error?.message, tasksCount: tasks.length, tasksResponse });
  }

  if (error) {
    return (
      <div className="tasks-page">
        <div className="tasks-page__error">
          <p>Failed to load tasks: {error.message}</p>
          <Button onClick={refresh}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="tasks-page">
      <div className="tasks-page__header">
        <h2>Tasks</h2>
        <Button variant="outline" onClick={refresh} disabled={isLoading}>
          {isLoading ? "..." : "Refresh"}
        </Button>
      </div>

      {isLoading && !tasksResponse ? (
        <div className="tasks-page__loading">Loading tasks...</div>
      ) : tasks.length === 0 ? (
        <div className="tasks-page__empty">
          <p>No tasks yet.</p>
          <p>Tasks will appear here when agents create them.</p>
        </div>
      ) : (
        <div className="tasks-list">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onView={() => handleViewTask(task)}
              onDelete={() => setDeleteConfirm(task.id)}
            />
          ))}
        </div>
      )}

      <TaskDetailModal
        task={selectedTask}
        taskDetail={taskDetail}
        isLoading={isLoadingDetail}
        onClose={handleCloseDetail}
      />

      <Modal
        isOpen={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        title="Delete Task"
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => deleteConfirm && handleDeleteTask(deleteConfirm)}
            >
              Delete
            </Button>
          </>
        }
      >
        <p>Are you sure you want to delete this task? This action cannot be undone.</p>
      </Modal>
    </div>
  );
}

interface TaskCardProps {
  task: Task;
  onView: () => void;
  onDelete: () => void;
}

function TaskCard({ task, onView, onDelete }: TaskCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="task-card__header">
          <code className="task-card__id">{task.id.slice(0, 8)}...</code>
          <TaskStatusBadge state={task.status.state} />
        </div>
      </CardHeader>
      <CardBody>
        <div className="task-card__meta">
          <div className="task-card__row">
            <strong>Context:</strong>
            <code>{task.context_id.slice(0, 8)}...</code>
          </div>
          {task.status.message && (
            <div className="task-card__row">
              <strong>Message:</strong>
              <span>{typeof task.status.message === "string" ? task.status.message : "See details"}</span>
            </div>
          )}
          <div className="task-card__row">
            <strong>Updated:</strong>
            <span>{new Date(task.status.timestamp).toLocaleString()}</span>
          </div>
          {task.history && (
            <div className="task-card__row">
              <strong>Messages:</strong>
              <span>{task.history.length}</span>
            </div>
          )}
        </div>
      </CardBody>
      <CardFooter>
        <Button variant="outline" size="sm" onClick={onView}>
          View Details
        </Button>
        <Button variant="danger" size="sm" onClick={onDelete}>
          Delete
        </Button>
      </CardFooter>
    </Card>
  );
}

function TaskStatusBadge({ state }: { state: TaskStateType }) {
  const variantMap: Record<TaskStateType, "default" | "primary" | "success" | "danger" | "warning"> = {
    submitted: "default",
    working: "primary",
    completed: "success",
    failed: "danger",
    cancelled: "default",
    input_required: "warning",
    rejected: "danger",
    auth_required: "warning",
  };

  return (
    <Badge variant={variantMap[state]} size="sm">
      {state.replace("_", " ")}
    </Badge>
  );
}

interface TaskDetailModalProps {
  task: Task | null;
  taskDetail: Task | null;
  isLoading: boolean;
  onClose: () => void;
}

function TaskDetailModal({ task, taskDetail, isLoading, onClose }: TaskDetailModalProps) {
  const [activeView, setActiveView] = useState<"info" | "history" | "artifacts">("history");

  if (!task) return null;

  const detail = taskDetail || task;

  return (
    <Modal isOpen={!!task} onClose={onClose} title={`Task: ${task.id.slice(0, 8)}...`}>
      <div className="task-detail">
        <div className="task-detail__tabs">
          <button
            className={`task-detail__tab ${activeView === "history" ? "active" : ""}`}
            onClick={() => setActiveView("history")}
          >
            Conversation ({detail.history?.length || 0})
          </button>
          <button
            className={`task-detail__tab ${activeView === "info" ? "active" : ""}`}
            onClick={() => setActiveView("info")}
          >
            Info
          </button>
          <button
            className={`task-detail__tab ${activeView === "artifacts" ? "active" : ""}`}
            onClick={() => setActiveView("artifacts")}
          >
            Artifacts ({detail.artifacts?.length || 0})
          </button>
        </div>

        {isLoading ? (
          <div className="task-detail__loading">Loading task details...</div>
        ) : (
          <>
            {activeView === "info" && (
              <div className="task-detail__section">
                <div className="task-detail__row">
                  <strong>Task ID:</strong>
                  <code>{detail.id}</code>
                </div>
                <div className="task-detail__row">
                  <strong>Context ID:</strong>
                  <code>{detail.context_id}</code>
                </div>
                <div className="task-detail__row">
                  <strong>Status:</strong>
                  <TaskStatusBadge state={detail.status.state} />
                </div>
                {detail.status.message && (
                  <div className="task-detail__row">
                    <strong>Status Message:</strong>
                    <span>{typeof detail.status.message === "string" ? detail.status.message : JSON.stringify(detail.status.message)}</span>
                  </div>
                )}
                <div className="task-detail__row">
                  <strong>Last Updated:</strong>
                  <span>{new Date(detail.status.timestamp).toLocaleString()}</span>
                </div>
                {detail.metadata && Object.keys(detail.metadata).length > 0 && (
                  <div className="task-detail__row">
                    <strong>Metadata:</strong>
                    <pre className="task-detail__json">
                      {JSON.stringify(detail.metadata, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {activeView === "history" && (
              <div className="task-detail__section">
                <ConversationHistory messages={detail.history || []} />
              </div>
            )}

            {activeView === "artifacts" && (
              <div className="task-detail__section">
                <ArtifactsList artifacts={detail.artifacts || []} />
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}

function ConversationHistory({ messages }: { messages: Message[] }) {
  if (messages.length === 0) {
    return <p className="task-detail__empty">No conversation history.</p>;
  }

  return (
    <div className="conversation">
      {messages.map((message) => (
        <div
          key={message.message_id}
          className={`conversation__message conversation__message--${message.role}`}
        >
          <div className="conversation__header">
            <Badge variant={message.role === "user" ? "primary" : "default"} size="sm">
              {message.role}
            </Badge>
          </div>
          <div className="conversation__content">
            {message.parts.map((part, idx) => (
              <MessagePart key={idx} part={part} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function MessagePart({ part }: { part: Part }) {
  // Handle backend format (no type field, check which property exists)
  const backendPart = part as { text?: string; file?: { name?: string; media_type?: string }; data?: { data?: Record<string, unknown> } };

  if (backendPart.text !== undefined) {
    return <p className="message-part message-part--text">{backendPart.text}</p>;
  }

  if (backendPart.file) {
    return (
      <div className="message-part message-part--file">
        <strong>File:</strong> {backendPart.file.name || "Unknown"} ({backendPart.file.media_type || "unknown"})
      </div>
    );
  }

  if (backendPart.data) {
    return (
      <pre className="message-part message-part--data">
        {JSON.stringify(backendPart.data.data || backendPart.data, null, 2)}
      </pre>
    );
  }

  // Fallback for frontend format (with type field)
  if ("type" in part) {
    switch (part.type) {
      case "text":
        return <p className="message-part message-part--text">{part.text}</p>;
      case "file":
        return (
          <div className="message-part message-part--file">
            <strong>File:</strong> {part.file.name} ({part.file.mime_type})
          </div>
        );
      case "data":
        return (
          <pre className="message-part message-part--data">
            {JSON.stringify(part.data, null, 2)}
          </pre>
        );
    }
  }

  return null;
}

function ArtifactsList({ artifacts }: { artifacts: Task["artifacts"] }) {
  if (!artifacts || artifacts.length === 0) {
    return <p className="task-detail__empty">No artifacts.</p>;
  }

  return (
    <div className="artifacts-list">
      {artifacts.map((artifact, idx) => (
        <div key={idx} className="artifact-item">
          <div className="artifact-item__header">
            <strong>{artifact.name || `Artifact ${artifact.index}`}</strong>
          </div>
          {artifact.description && (
            <p className="artifact-item__description">{artifact.description}</p>
          )}
          <div className="artifact-item__parts">
            {artifact.parts.map((part, partIdx) => (
              <MessagePart key={partIdx} part={part} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
