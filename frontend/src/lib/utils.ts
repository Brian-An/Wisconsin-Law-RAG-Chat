import type { Conversation, Message } from "./types";

export function deriveTitle(firstMessage: string): string {
  const cleaned = firstMessage.replace(/\s+/g, " ").trim();
  return cleaned.length > 40 ? cleaned.substring(0, 40) + "..." : cleaned;
}

export function groupConversations(conversations: Conversation[]): {
  today: Conversation[];
  yesterday: Conversation[];
  older: Conversation[];
} {
  const todayStart = new Date().setHours(0, 0, 0, 0);
  const yesterdayStart = todayStart - 86_400_000;

  const sorted = [...conversations].sort((a, b) => b.updated_at - a.updated_at);

  return {
    today: sorted.filter((c) => c.updated_at >= todayStart),
    yesterday: sorted.filter(
      (c) => c.updated_at >= yesterdayStart && c.updated_at < todayStart,
    ),
    older: sorted.filter((c) => c.updated_at < yesterdayStart),
  };
}

export function formatForReport(message: Message): string {
  let text = message.content;

  // Strip markdown formatting
  text = text.replace(/\*\*(.*?)\*\*/g, "$1");
  text = text.replace(/\*(.*?)\*/g, "$1");
  text = text.replace(/`(.*?)`/g, "$1");
  text = text.replace(/^#{1,6}\s+/gm, "");
  text = text.replace(/^[-*]\s+/gm, "- ");

  // Append sources
  if (message.sources && message.sources.length > 0) {
    text += "\n\nSources:\n";
    message.sources.forEach((src, i) => {
      text += `${i + 1}. ${src.title}`;
      if (src.context_header) text += ` (${src.context_header})`;
      text += "\n";
    });
  }

  return text.trim();
}

export function getConfidenceLevel(score: number): "high" | "medium" | "low" {
  if (score > 0.9) return "high";
  if (score > 0.6) return "medium";
  return "low";
}

export function formatConversationForReport(
  conversation: Conversation,
): string {
  const header = [
    "====================================",
    "CASE REFERENCE / REPORT EXPORT",
    "====================================",
    `Conversation: ${conversation.title}`,
    `Date: ${new Date(conversation.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}`,
    `Session ID: ${conversation.session_id}`,
    `Total Messages: ${conversation.messages.length}`,
    "------------------------------------",
    "",
  ].join("\n");

  const body = conversation.messages
    .map((msg) => {
      const timestamp = new Date(msg.timestamp).toLocaleString("en-US");
      const role = msg.role === "user" ? "OFFICER QUERY" : "SYSTEM RESPONSE";
      let entry = `[${timestamp}] ${role}:\n${formatForReport(msg)}`;

      if (msg.role === "assistant") {
        if (msg.confidence_score !== undefined) {
          const level = getConfidenceLevel(msg.confidence_score);
          entry += `\nConfidence: ${(msg.confidence_score * 100).toFixed(0)}% (${level})`;
        }
        if (msg.flags) {
          const activeFlags = Object.entries(msg.flags)
            .filter(([, v]) => v)
            .map(([k]) => k);
          if (activeFlags.length > 0) {
            entry += `\nFlags: ${activeFlags.join(", ")}`;
          }
        }
        if (msg.disclaimer) {
          entry += `\nDisclaimer: ${msg.disclaimer}`;
        }
      }
      return entry;
    })
    .join("\n\n------------------------------------\n\n");

  const footer = [
    "",
    "====================================",
    "END OF EXPORT",
    `Generated: ${new Date().toLocaleString("en-US")}`,
    "This system provides legal information, not formal legal advice.",
    "====================================",
  ].join("\n");

  return `${header}${body}\n${footer}`;
}
