import React from "react";

const STOPWORDS = new Set([
  "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
  "have", "has", "had", "do", "does", "did", "will", "would", "shall",
  "should", "may", "might", "can", "could", "must", "of", "in", "on",
  "at", "to", "for", "with", "by", "from", "as", "into", "about",
  "and", "or", "but", "not", "no", "if", "then", "so", "it", "its",
  "this", "that", "these", "those", "what", "which", "who", "whom",
  "how", "when", "where", "why", "i", "me", "my", "we", "our", "you",
  "your", "he", "she", "they", "them", "their",
]);

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Highlight keywords from a query within text, returning React nodes.
 * Stopwords are filtered out. Returns plain text if no query or no matches.
 */
export function highlightKeywords(
  text: string,
  query?: string | null,
): React.ReactNode {
  if (!query || !text) return text;

  const keywords = query
    .split(/\s+/)
    .map((w) => w.toLowerCase().replace(/[^a-z0-9]/g, ""))
    .filter((w) => w.length > 1 && !STOPWORDS.has(w));

  if (keywords.length === 0) return text;

  const pattern = new RegExp(
    `(${keywords.map(escapeRegex).join("|")})`,
    "gi",
  );

  const parts = text.split(pattern);

  return parts.map((part, i) =>
    pattern.test(part) ? (
      <mark key={i} className="keyword-highlight">
        {part}
      </mark>
    ) : (
      part
    ),
  );
}
