"use client";

import { useActionState, useRef, useEffect, useState } from "react";
import { saveModelCredentialAction } from "./model-credential-actions";
import { Button } from "@/components/ui/button";
import {
  MODEL_PROVIDERS,
  PROVIDER_INFO,
  type ModelProvider,
} from "@/lib/model-providers";

const initialState = { error: null, success: false };

const INPUT_CLASS =
  "h-10 rounded-md border-2 border-border bg-background px-3 text-sm outline-none focus-visible:border-foreground focus-visible:ring-3 focus-visible:ring-ring/50";

export function ConnectModelCredentialForm() {
  const [state, formAction, isPending] = useActionState(saveModelCredentialAction, initialState);
  const [provider, setProvider] = useState<ModelProvider>("gemini");
  const [model, setModel] = useState(PROVIDER_INFO.gemini.defaultModel);
  const formRef = useRef<HTMLFormElement>(null);
  const info = PROVIDER_INFO[provider];

  useEffect(() => {
    if (state.success) formRef.current?.reset();
  }, [state.success]);

  return (
    <form ref={formRef} action={formAction} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="provider" className="text-sm font-semibold">
          Provider
        </label>
        <select
          id="provider"
          name="provider"
          value={provider}
          onChange={(e) => {
            const next = e.target.value as ModelProvider;
            setProvider(next);
            setModel(PROVIDER_INFO[next].defaultModel);
          }}
          className={INPUT_CLASS}
        >
          {MODEL_PROVIDERS.map((p) => (
            <option key={p} value={p}>
              {PROVIDER_INFO[p].label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="model" className="text-sm font-semibold">
          Model
        </label>
        <input
          id="model"
          name="model"
          type="text"
          autoComplete="off"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          required
          className={`${INPUT_CLASS} font-mono`}
        />
        <p className="text-xs text-muted-foreground">
          The default works on the free tier. If it is rejected, the error
          lists the models your key can use.
        </p>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="api_key" className="text-sm font-semibold">
          API key
        </label>
        <input
          id="api_key"
          name="api_key"
          type="password"
          autoComplete="off"
          placeholder={info.keyPlaceholder}
          required
          className={`${INPUT_CLASS} font-mono`}
        />
        <p className="text-xs text-muted-foreground">
          Get a key at{" "}
          <a
            href={info.keyUrl}
            target="_blank"
            rel="noreferrer"
            className="font-semibold text-foreground underline decoration-lime decoration-2 underline-offset-2"
          >
            {info.keyUrl.replace("https://", "")}
          </a>
          . It is encrypted before it is stored.
        </p>
      </div>

      {state.error && (
        <p className="rounded-md border-2 border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {state.error}
        </p>
      )}
      {state.success && (
        <p className="text-sm text-emerald-600 dark:text-emerald-400">
          Provider connected.
        </p>
      )}

      <Button type="submit" disabled={isPending} className="self-start">
        {isPending ? "Checking key..." : "Connect provider"}
      </Button>
    </form>
  );
}
