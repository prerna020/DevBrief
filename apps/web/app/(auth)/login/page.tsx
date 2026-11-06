import Link from "next/link";

import { signIn } from "@/auth";
import { Logo } from "@/components/brand/logo";
import { SignInButton } from "./sign-in-button";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string }>;
}) {
  const { callbackUrl } = await searchParams;

  return (
    <div className="w-full max-w-[420px]">
      <Link href="/" aria-label="DevBrief home" className="lg:hidden">
        <Logo />
      </Link>

      <p className="mt-8 font-mono text-xs uppercase tracking-widest text-muted-foreground lg:mt-0">
        Welcome
      </p>
      <h1 className="mt-2 text-4xl font-extrabold tracking-tighter">
        Sign in to <span className="mark-lime">DevBrief</span>
      </h1>
      <p className="mt-3 text-muted-foreground">
        Continue with your GitHub account to get started.
      </p>

      <form
        className="mt-8 w-full"
        action={async () => {
          "use server";
          await signIn("github", { redirectTo: callbackUrl ?? "/dashboard" });
        }}
      >
        <SignInButton />
      </form>

      <p className="mt-6 text-xs text-muted-foreground">
        By continuing, you agree to our Terms and Privacy Policy.
      </p>
    </div>
  );
}
