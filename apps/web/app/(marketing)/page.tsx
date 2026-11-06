import Link from "next/link";
import { ArrowRight, GitPullRequest, KeyRound, Terminal, Workflow } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/marketing/reveal";
import { ReviewMock, TerminalMock } from "@/components/marketing/mocks";

const STEPS = [
  {
    n: "01",
    title: "Connect",
    desc: "Install the GitHub App on a repo, or install the CLI. Add your own model key (a free Groq key works) and you are set.",
  },
  {
    n: "02",
    title: "Push a change",
    desc: "Open a pull request, or run a review on your staged changes from the terminal.",
  },
  {
    n: "03",
    title: "Read the brief",
    desc: "Findings land on the exact lines that cause them, ranked by severity, with a suggested fix.",
  },
];

const AVAILABLE_NOW = [
  {
    icon: GitPullRequest,
    title: "Inline PR reviews",
    desc: "Comments on the exact lines, a summary, and an optional pass/fail check.",
  },
  {
    icon: Terminal,
    title: "Local CLI reviews",
    desc: "Review staged, uncommitted, or committed changes before you push.",
  },
  {
    icon: KeyRound,
    title: "Bring your own key",
    desc: "Use your own model provider key. No shared bill, no lock-in.",
  },
  {
    icon: Workflow,
    title: "Dashboard analytics",
    desc: "Track reviews, findings by severity, and connected repos.",
  },
];

const COMING_SOON = [
  "Slack digests",
  "Discord alerts",
  "Deeper codebase context",
  "Review memory",
  "MCP tools",
];

export default function LandingPage() {
  return (
    <>
      <HeroSection />
      <TickerStrip />
      <Reveal>
        <HowItWorksSection />
      </Reveal>
      <Reveal>
        <SurfacesSection />
      </Reveal>
      <Reveal>
        <FeatureSection />
      </Reveal>
      <Reveal>
        <CtaBand />
      </Reveal>
    </>
  );
}

function HeroSection() {
  return (
    <section className="bg-grid border-b-2 border-foreground">
      <div className="mx-auto grid max-w-6xl items-center gap-14 px-6 py-16 sm:px-10 lg:grid-cols-[1.05fr_1fr] lg:py-24">
        <div>
          <span
            className="rise inline-flex items-center gap-2 rounded-md border-2 border-foreground bg-card px-3 py-1 font-mono text-xs"
          >
            <span className="size-2 rounded-full bg-lime ring-1 ring-foreground" />
            Bring your own model key
          </span>

          <h1
            className="rise mt-6 text-5xl leading-[0.98] font-extrabold tracking-tighter sm:text-6xl lg:text-7xl"
            style={{ animationDelay: "80ms" }}
          >
            Your pull requests,{" "}
            <span className="mark-lime">briefed</span> before anyone opens them.
          </h1>

          <p
            className="rise mt-6 max-w-lg text-lg text-muted-foreground"
            style={{ animationDelay: "160ms" }}
          >
            DevBrief reads every diff, flags the bugs and security holes on the
            lines that cause them, and leaves your teammates with the parts
            that need a human.
          </p>

          <div
            className="rise mt-8 flex flex-wrap items-center gap-3"
            style={{ animationDelay: "240ms" }}
          >
            <Button size="lg" variant="lime" render={<Link href="/login" />}>
              Start reviewing
              <ArrowRight className="size-4" />
            </Button>
            <Button size="lg" variant="outline" render={<Link href="/docs" />}>
              Read the docs
            </Button>
          </div>
        </div>

        <div className="rise relative" style={{ animationDelay: "200ms" }}>
          <ReviewMock />
        </div>
      </div>
    </section>
  );
}

function TickerStrip() {
  const items = [
    "SQL injection",
    "Null dereference",
    "Hardcoded secrets",
    "Race conditions",
    "Unchecked input",
    "Resource leaks",
    "Off-by-one",
    "Unsafe deserialization",
  ];
  return (
    <div className="overflow-hidden border-b-2 border-foreground bg-lime py-3 text-lime-foreground">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-8 gap-y-2 px-6 font-mono text-xs font-semibold uppercase tracking-widest">
        {items.map((item) => (
          <span key={item}>/ {item}</span>
        ))}
      </div>
    </div>
  );
}

function HowItWorksSection() {
  return (
    <section id="how-it-works" className="scroll-mt-20 px-6 py-24 sm:px-10">
      <div className="mx-auto max-w-6xl">
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          How it works
        </p>
        <h2 className="mt-3 max-w-2xl text-4xl font-extrabold tracking-tighter sm:text-5xl">
          Three steps from push to <span className="mark-lime">review</span>.
        </h2>

        <ol className="mt-14 grid gap-6 md:grid-cols-3">
          {STEPS.map((s) => (
            <li
              key={s.n}
              className="relative rounded-xl border-2 border-foreground bg-card p-6 shadow-hard"
            >
              <span className="font-mono text-4xl font-bold text-lime [-webkit-text-stroke:2px_var(--foreground)]">
                {s.n}
              </span>
              <h3 className="mt-4 text-2xl font-bold tracking-tight">{s.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{s.desc}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function SurfacesSection() {
  return (
    <section className="border-y-2 border-foreground bg-secondary px-6 py-24 sm:px-10">
      <div className="mx-auto max-w-6xl">
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          Two ways in
        </p>
        <h2 className="mt-3 text-4xl font-extrabold tracking-tighter sm:text-5xl">
          Review where you already work.
        </h2>

        <div className="mt-14 grid gap-8 lg:grid-cols-2">
          <div className="flex flex-col gap-5">
            <div>
              <h3 className="text-2xl font-bold tracking-tight">GitHub App</h3>
              <p className="mt-2 text-muted-foreground">
                Every opened or updated pull request gets inline comments, a
                summary, and an optional required check.
              </p>
            </div>
            <ReviewMock className="mt-auto" />
            <Button variant="outline" className="self-start" render={<Link href="/install" />}>
              Install the app
              <ArrowRight className="size-4" />
            </Button>
          </div>

          <div className="flex flex-col gap-5">
            <div>
              <h3 className="text-2xl font-bold tracking-tight">Command line</h3>
              <p className="mt-2 text-muted-foreground">
                Catch problems before you push. Review a diff from your
                terminal without touching GitHub.
              </p>
            </div>
            <TerminalMock className="mt-auto" />
            <Button variant="outline" className="self-start" render={<Link href="/install" />}>
              Install the CLI
              <ArrowRight className="size-4" />
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}

function FeatureSection() {
  return (
    <section className="px-6 py-24 sm:px-10">
      <div className="mx-auto max-w-6xl">
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          Features
        </p>
        <h2 className="mt-3 text-4xl font-extrabold tracking-tighter sm:text-5xl">
          Built for teams that ship fast.
        </h2>

        <div className="mt-14 grid gap-5 sm:grid-cols-2">
          {AVAILABLE_NOW.map((f) => (
            <div
              key={f.title}
              className="group flex gap-4 rounded-xl border-2 border-border bg-card p-6 transition-colors hover:border-foreground"
            >
              <span className="flex size-11 shrink-0 items-center justify-center rounded-md bg-lime text-lime-foreground">
                <f.icon className="size-5" strokeWidth={2} />
              </span>
              <div>
                <h3 className="text-lg font-bold tracking-tight">{f.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap items-center gap-2">
          <span className="mr-2 font-mono text-xs uppercase tracking-widest text-muted-foreground">
            Coming soon
          </span>
          {COMING_SOON.map((c) => (
            <span
              key={c}
              className="rounded-full border-2 border-dashed border-border px-3 py-1 text-sm text-muted-foreground"
            >
              {c}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function CtaBand() {
  return (
    <section className="px-6 pb-24 sm:px-10">
      <div className="bg-grid-light mx-auto max-w-6xl rounded-2xl border-2 border-foreground bg-ink p-10 text-ink-foreground shadow-hard sm:p-16">
        <h2 className="max-w-2xl text-4xl font-extrabold tracking-tighter sm:text-5xl">
          Get the brief on your next pull request.
        </h2>
        <p className="mt-4 max-w-lg text-ink-foreground/70">
          Sign in with GitHub, add your own model key, and open a PR.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button
            size="lg"
            variant="lime"
            className="border-lime"
            render={<Link href="/login" />}
          >
            Start reviewing
            <ArrowRight className="size-4" />
          </Button>
        </div>
      </div>
    </section>
  );
}
