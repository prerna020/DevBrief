"use client"

import { useState } from "react"
import { Check, Copy } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

function CodeBlock({
  code,
  className,
  prompt = true,
}: {
  code: string
  className?: string
  prompt?: boolean
}) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div
      className={cn(
        "flex items-start justify-between gap-3 rounded-md border border-ink bg-ink px-4 py-3 text-ink-foreground",
        className
      )}
    >
      <code className="overflow-x-auto whitespace-pre font-mono text-[13px] leading-relaxed">
        {prompt && <span className="select-none text-lime">$ </span>}
        {code}
      </code>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Copy to clipboard"
        className="text-ink-foreground hover:bg-white/10 hover:text-lime"
        onClick={handleCopy}
      >
        {copied ? (
          <Check className="size-3.5" />
        ) : (
          <Copy className="size-3.5" />
        )}
      </Button>
    </div>
  )
}

export { CodeBlock }
