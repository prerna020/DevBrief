/**
 * LLM providers a user can connect (BYOK). All three expose an
 * OpenAI-compatible API; the ai-engine mirrors these base URLs in
 * `services/ai-engine/app/nodes/review.py`.
 */
export const MODEL_PROVIDERS = ["gemini", "groq", "openrouter"] as const;
export type ModelProvider = (typeof MODEL_PROVIDERS)[number];

export const PROVIDER_INFO: Record<
  ModelProvider,
  {
    label: string;
    baseUrl: string;
    defaultModel: string;
    keyPlaceholder: string;
    keyUrl: string;
  }
> = {
  gemini: {
    label: "Google Gemini (free tier)",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
    defaultModel: "gemini-flash-lite-latest",
    keyPlaceholder: "AIza...",
    keyUrl: "https://aistudio.google.com/apikey",
  },
  groq: {
    label: "Groq (free tier)",
    baseUrl: "https://api.groq.com/openai/v1",
    defaultModel: "openai/gpt-oss-20b",
    keyPlaceholder: "gsk_...",
    keyUrl: "https://console.groq.com/keys",
  },
  openrouter: {
    label: "OpenRouter",
    baseUrl: "https://openrouter.ai/api/v1",
    defaultModel: "openai/gpt-oss-20b:free",
    keyPlaceholder: "sk-or-...",
    keyUrl: "https://openrouter.ai/keys",
  },
};

export function isModelProvider(value: string): value is ModelProvider {
  return (MODEL_PROVIDERS as readonly string[]).includes(value);
}

async function listModelIds(provider: ModelProvider, apiKey: string): Promise<string[]> {
  try {
    const res = await fetch(`${PROVIDER_INFO[provider].baseUrl}/models`, {
      headers: { Authorization: `Bearer ${apiKey}` },
      cache: "no-store",
    });
    if (!res.ok) return [];
    const body = (await res.json()) as { data?: { id?: string }[] };
    return (body.data ?? [])
      .map((m) => (m.id ?? "").replace(/^models\//, ""))
      .filter(Boolean);
  } catch {
    return [];
  }
}

/**
 * Sends a tiny chat completion with the user's key and model so a bad key or
 * a wrong model id is reported when they save, not on their first review.
 * Returns null when the credential works, or a user-facing error message.
 */
export async function verifyModelCredential(
  provider: ModelProvider,
  model: string,
  apiKey: string
): Promise<string | null> {
  const info = PROVIDER_INFO[provider];
  let res: Response;
  try {
    res = await fetch(`${info.baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: "Reply with OK." }],
        max_tokens: 5,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });
  } catch {
    return `Could not reach ${info.label}. Check your internet connection and try again.`;
  }

  if (res.ok) return null;
  // Rate-limited means the key and model were accepted; save it.
  if (res.status === 429) return null;

  const text = await res.text().catch(() => "");
  if (res.status === 401 || res.status === 403) {
    return `${info.label} rejected this API key. Create a new one at ${info.keyUrl}.`;
  }

  const looksLikeBadModel =
    res.status === 404 || /model/i.test(text);
  if (looksLikeBadModel) {
    const ids = await listModelIds(provider, apiKey);
    const suggestions = ids.slice(0, 12).join(", ");
    return suggestions
      ? `Model "${model}" was not accepted. Models your key can use include: ${suggestions}`
      : `Model "${model}" was not accepted by ${info.label}. Check the model id.`;
  }

  return `${info.label} returned ${res.status}: ${text.slice(0, 300)}`;
}
