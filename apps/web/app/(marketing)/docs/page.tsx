import Link from "next/link";
import { GitFork, Terminal, FileCode, BookOpen } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { CodeBlock } from "@/components/code-block";

const CLI_CONFIG_PATHS = [
  { os: "Linux", path: "~/.config/devbrief/config.toml" },
  { os: "macOS", path: "~/Library/Application Support/devbrief/config.toml" },
  { os: "Windows", path: "%LOCALAPPDATA%\\devbrief\\devbrief\\config.toml" },
];

const CONFIG_YML_EXAMPLE = `# .devbrief.yml — place at the root of your repo
ignore_paths:
  - "vendor/**"
  - "**/*.generated.ts"

# Findings below this severity are dropped before DevBrief comments.
# One of: critical, warning, info
min_severity: warning

# Caps the number of inline comments DevBrief leaves on a single PR.
# If more findings pass the severity filter than this, the most
# severe ones are kept and the rest are silently dropped.
max_comments_per_pr: 10

# If true, DevBrief creates a GitHub Check Run on each PR that fails
# whenever the review finds any critical-severity issue. Off by
# default — turning this on is what lets you require DevBrief to pass
# via GitHub's branch protection settings.
require_check: false
`;

function SubSection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div id={id} className="scroll-mt-16">
      <h3 className="text-sm font-medium">{title}</h3>
      <div className="mt-2 flex flex-col gap-3">{children}</div>
    </div>
  );
}

export default function DocsPage() {
  return (
    <div className="flex flex-col gap-10">
      <div>
        <h1 className="text-3xl font-medium tracking-tight sm:text-4xl">
          Docs
        </h1>
        <p className="mt-3 text-muted-foreground">
          Everything you need to get DevBrief reviewing your pull requests, or
          running locally from the CLI.
        </p>
      </div>

      {/* Introduction */}
      <Card id="introduction" className="scroll-mt-16">
        <CardHeader>
          <BookOpen className="size-6 text-foreground" />
          <CardTitle className="mt-2">Introduction</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">
            DevBrief is an automated code review tool. It reads the diff of a
            change, inspects it against the repository&apos;s configuration,
            and reports concrete findings — security issues, error-prone
            patterns, and likely bugs — on the exact lines that cause them.
          </p>
          <p className="text-sm text-muted-foreground">DevBrief has two surfaces:</p>
          <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm text-muted-foreground">
            <li>
              <strong className="font-medium text-foreground">
                GitHub App
              </strong>{" "}
              — reviews every pull request automatically with inline
              comments, a summary, and an optional pass/fail check.
            </li>
            <li>
              <strong className="font-medium text-foreground">CLI</strong> —
              reviews staged, uncommitted, or committed changes locally.
            </li>
          </ul>
          <p className="text-sm text-muted-foreground">
            DevBrief is open architecture, not a black box — the GitHub App,
            worker, and AI engine are separate services that only talk over
            HTTP. Self-hosting docs are on the way; for now, the hosted
            version is the easiest way to run DevBrief.
          </p>
        </CardContent>
      </Card>

      {/* Getting started */}
      <Card id="getting-started" className="scroll-mt-16">
        <CardHeader>
          <GitFork className="size-6 text-foreground" />
          <CardTitle className="mt-2">Getting started</CardTitle>
          <CardDescription>
            Two ways to use DevBrief — pick one or use both.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <SubSection id="installation" title="Installation">
            <div>
              <h4 className="text-sm font-medium">GitHub App</h4>
              <p className="mt-1 text-sm text-muted-foreground">
                Install the app on a repo and DevBrief reviews every pull request
                automatically.
              </p>
              <Button className="mt-3" render={<Link href="/install" />}>
                Install on GitHub
              </Button>
            </div>
            <div>
              <h4 className="text-sm font-medium">CLI</h4>
              <p className="mt-1 text-sm text-muted-foreground">
                The CLI is not published as a public package yet. Follow
                <code className="font-mono"> LOCAL_SETUP.md</code> in the
                repository to install it from source (Python 3.12+).
              </p>
            </div>
          </SubSection>

          <SubSection id="quickstart" title="Quickstart">
            <p className="text-sm text-muted-foreground">
              With the CLI, your first review is three steps:
            </p>
            <ol className="flex list-decimal flex-col gap-3 pl-5 text-sm text-muted-foreground">
              <li>
                Create an API key from your{" "}
                <Link href="/dashboard/api-keys" className="underline">
                  dashboard
                </Link>
                .
              </li>
              <li>
                Authenticate the CLI — it validates your key and stores it in
                your platform&apos;s DevBrief config file (see its exact
                location below):
                <CodeBlock code="devbrief auth" className="mt-2" />
              </li>
              <li>
                Review staged changes from inside any git repository:
                <CodeBlock code="devbrief review --staged" className="mt-2" />
              </li>
            </ol>
            <p className="text-sm text-muted-foreground">
              With the GitHub App, it&apos;s just: install the app, open a
              pull request, and read the comments it leaves on your diff.
            </p>
          </SubSection>
        </CardContent>
      </Card>

      {/* GitHub App */}
      <Card id="github-app" className="scroll-mt-16">
        <CardHeader>
          <GitFork className="size-6 text-foreground" />
          <CardTitle className="mt-2">GitHub App</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <SubSection id="installing-app" title="Installing the app">
            <p className="text-sm text-muted-foreground">
              Head to the{" "}
              <Link href="/install" className="underline">
                install page
              </Link>
              , sign in, and grant DevBrief access to the repositories you want
              reviewed. You can pick all of a user&apos;s or org&apos;s repos,
              or a specific subset, and you can revoke or edit access at any
              time from GitHub&apos;s app settings.
            </p>
            <p className="text-sm text-muted-foreground">
              Repositories added to the app later are picked up automatically
              — no reinstall needed.
            </p>
          </SubSection>

          <SubSection id="how-reviews-work" title="How reviews work">
            <p className="text-sm text-muted-foreground">
              When a pull request is opened or updated, the GitHub App hands
              the job to DevBrief&apos;s worker, which:
            </p>
            <ol className="flex list-decimal flex-col gap-1.5 pl-5 text-sm text-muted-foreground">
              <li>
                Builds the diff between the base and head of the PR.
              </li>
              <li>
                Reads <code className="font-mono">.devbrief.yml</code> from the
                exact commit being reviewed.
              </li>
              <li>
                Sends both to the AI engine, which returns findings scoped to
                changed lines.
              </li>
              <li>
                Posts the findings as inline comments, adds a summary comment,
                and — if configured — creates a GitHub Check Run.
              </li>
            </ol>
          </SubSection>
        </CardContent>
      </Card>

      {/* CLI */}
      <Card id="cli" className="scroll-mt-16">
        <CardHeader>
          <Terminal className="size-6 text-foreground" />
          <CardTitle className="mt-2">CLI</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <SubSection id="cli-install" title="Installation">
            <p className="text-sm text-muted-foreground">
              The CLI is not published as a public package yet. Install it
              from the repository with{" "}
              <code className="font-mono">uv tool install --editable ./apps/cli</code>{" "}
              (Python 3.12+), as described in{" "}
              <code className="font-mono">LOCAL_SETUP.md</code>.
            </p>
          </SubSection>

          <SubSection id="cli-auth" title="Authentication (API keys)">
            <ol className="flex list-decimal flex-col gap-3 pl-5 text-sm text-muted-foreground">
              <li>
                Create a key from your{" "}
                <Link href="/dashboard/api-keys" className="underline">
                  dashboard
                </Link>
                .
              </li>
              <li>
                Run <code className="font-mono">devbrief auth</code> and paste it
                when prompted:
                <CodeBlock code="devbrief auth" className="mt-2" />
              </li>
            </ol>
            <p className="text-sm text-muted-foreground">
              <code className="font-mono">devbrief auth</code> checks the key
              against DevBrief before saving it, then writes it to your
              platform&apos;s DevBrief config file:
            </p>
            <div className="mt-3 flex flex-col gap-2 rounded-md border border-border p-3">
              <p className="text-xs font-medium text-foreground">
                Config file location
              </p>
              <ul className="flex flex-col gap-1.5">
                {CLI_CONFIG_PATHS.map((row) => (
                  <li
                    key={row.os}
                    className="flex items-baseline gap-2 text-xs text-muted-foreground"
                  >
                    <span className="w-16 shrink-0 font-medium text-foreground">
                      {row.os}
                    </span>
                    <code className="font-mono break-all">{row.path}</code>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-muted-foreground">
                The directory is created automatically on first run. On POSIX
                the file is written with{" "}
                <code className="font-mono">0600</code> permissions; on
                Windows it lives under your already-private{" "}
                <code className="font-mono">%LOCALAPPDATA%</code>.
              </p>
            </div>
            <p className="text-sm text-muted-foreground">
              Alternatively, write that file yourself:
            </p>
            <CodeBlock code={`[api]\napi_key = "devbrief_..."`} prompt={false} />
            <p className="text-sm text-muted-foreground">
              Before your first review, connect a Gemini, Groq, or OpenRouter key in
              the dashboard&apos;s settings so DevBrief can call your chosen LLM.
              Reviews fail with a clear error until one is configured.
            </p>
            <p className="text-sm text-muted-foreground">
              Keep this file private — anyone with your key can use your
              account&apos;s review quota. Revoke a key any time from the
              dashboard if it&apos;s ever exposed.
            </p>
          </SubSection>

          <SubSection id="cli-reference" title="Commands reference">
            <p className="text-sm text-muted-foreground">
              Run from inside any git repository.
            </p>
            <div className="flex flex-col gap-4">
              <div>
                <CodeBlock code="devbrief review --staged" />
                <p className="mt-2 text-sm text-muted-foreground">
                  Reviews changes that are staged (
                  <code className="font-mono">git add</code>-ed) but not yet
                  committed.
                </p>
              </div>
              <div>
                <CodeBlock code="devbrief review --uncommitted" />
                <p className="mt-2 text-sm text-muted-foreground">
                  Reviews all uncommitted changes in the working tree, staged
                  or not.
                </p>
              </div>
              <div>
                <CodeBlock code="devbrief review --committed" />
                <p className="mt-2 text-sm text-muted-foreground">
                  Reviews commits on your current branch that haven&apos;t
                  been pushed to its upstream yet.
                </p>
              </div>
              <div>
                <CodeBlock code="devbrief review --diff path/to/file.diff" />
                <p className="mt-2 text-sm text-muted-foreground">
                  Reviews a diff from a file instead of your working tree —
                  useful for CI or scripting.
                </p>
              </div>
              <div>
                <CodeBlock code="devbrief review --include-untracked" />
                <p className="mt-2 text-sm text-muted-foreground">
                  Add this to any of the above to also review new, untracked
                  files (treated as entirely-added diffs).
                </p>
              </div>
              <div>
                <CodeBlock code="devbrief review" />
                <p className="mt-2 text-sm text-muted-foreground">
                  With no flags, reviews committed-but-unpushed changes plus
                  anything uncommitted — whichever exist.
                </p>
              </div>
            </div>
          </SubSection>
        </CardContent>
      </Card>

      {/* Configuration */}
      <Card id="configuration" className="scroll-mt-16">
        <CardHeader>
          <FileCode className="size-6 text-foreground" />
          <CardTitle className="mt-2">Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <SubSection id="devbrief-yml" title=".devbrief.yml reference">
            <p className="text-sm text-muted-foreground">
              Drop this file at the root of your repo to tune what DevBrief
              comments on. Every field is optional — an absent or missing
              file just means DevBrief uses these defaults.
            </p>
            <CodeBlock code={CONFIG_YML_EXAMPLE} prompt={false} />
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-sm font-medium">ignore_paths</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  List of glob patterns. Files matching any pattern are
                  excluded before DevBrief ever sees them. Default: none.
                </p>
              </div>
              <div>
                <p className="text-sm font-medium">min_severity</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  One of <code className="font-mono">critical</code>,{" "}
                  <code className="font-mono">warning</code>,{" "}
                  <code className="font-mono">info</code>. Findings below
                  this are dropped. Default:{" "}
                  <code className="font-mono">info</code> (nothing filtered).
                </p>
              </div>
              <div>
                <p className="text-sm font-medium">max_comments_per_pr</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Caps inline comments per review. Most severe findings are
                  kept first. Default: <code className="font-mono">10</code>.
                </p>
              </div>
              <div>
                <p className="text-sm font-medium">require_check</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  If <code className="font-mono">true</code>, DevBrief creates a
                  GitHub Check Run that fails when the review finds any
                  critical issue. Default:{" "}
                  <code className="font-mono">false</code>.
                </p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              This file is read from the exact commit being reviewed, so a
              PR that changes <code className="font-mono">.devbrief.yml</code>{" "}
              takes effect on itself.
            </p>
            <p className="text-sm text-muted-foreground">
              <code className="font-mono">require_check</code> only creates
              the check — it doesn&apos;t block merging by itself. To
              actually require it, go to your repo&apos;s{" "}
              <strong>Settings → Branches → Branch protection rules</strong>,
              edit (or add) a rule for your target branch, and add{" "}
              <code className="font-mono">DevBrief</code> under &quot;Require
              status checks to pass before merging.&quot;
            </p>
          </SubSection>
        </CardContent>
      </Card>

      {/* Guides */}
      <Card id="guides" className="scroll-mt-16">
        <CardHeader>
          <BookOpen className="size-6 text-foreground" />
          <CardTitle className="mt-2">Guides</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <SubSection id="best-practices" title="Best practices">
            <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm text-muted-foreground">
              <li>
                <strong className="font-medium text-foreground">
                  Ignore generated code.
                </strong>{" "}
                Add build output, vendored deps, and generated files to{" "}
                <code className="font-mono">ignore_paths</code> so DevBrief focuses
                on code a human will actually review.
              </li>
              <li>
                <strong className="font-medium text-foreground">
                  Set a severity floor.
                </strong>{" "}
                Start with <code className="font-mono">min_severity: warning</code>{" "}
                to keep reviews focused, then widen as DevBrief earns trust.
              </li>
              <li>
                <strong className="font-medium text-foreground">
                  Gate CI on critical issues.
                </strong>{" "}
                Turn on <code className="font-mono">require_check</code> and
                require the DevBrief check via branch protection for a hard gate
                on merge.
              </li>
              <li>
                <strong className="font-medium text-foreground">
                  Keep scopes small.
                </strong>{" "}
                Review staged changes with{" "}
                <code className="font-mono">--staged</code> while working,
                and use <code className="font-mono">--diff file.diff</code> in
                CI scripts.
              </li>
            </ul>
          </SubSection>

          <SubSection id="troubleshooting" title="Troubleshooting">
            <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm text-muted-foreground">
              <li>
                <code className="font-mono">Error: not authenticated. Run
                devbrief auth first.</code> — the CLI has no key, or the key was
                revoked. Run <code className="font-mono">devbrief auth</code> with
                a key from your dashboard.
              </li>
              <li>
                <code className="font-mono">No LLM provider configured for
                this account.</code> — connect a Gemini, Groq, or OpenRouter key in
                the dashboard&apos;s settings before reviewing.
              </li>
              <li>
                <code className="font-mono">could not connect to
                ai-engine at ...</code> — the CLI can&apos;t reach the API.
                Check                 the <code className="font-mono">url</code> in your DevBrief config
                file (location varies by OS — see the CLI section above),
                or re-run <code className="font-mono">devbrief auth</code>.
              </li>
              <li>
                Reviews silently skip files or take long — very large diffs
                are capped to protect responsiveness. Prefer reviewing
                smaller, focused scopes.
              </li>
            </ul>
          </SubSection>
        </CardContent>
      </Card>
    </div>
  );
}