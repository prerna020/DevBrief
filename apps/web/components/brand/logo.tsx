import { cn } from "@/lib/utils";

/** Square lime mark with a stylised "brief" bracket pair. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex size-7 shrink-0 items-center justify-center rounded-md bg-lime font-mono text-[13px] font-bold leading-none text-lime-foreground ring-1 ring-black/10",
        className
      )}
    >
      {"{}"}
    </span>
  );
}

export function Logo({
  className,
  textClassName,
}: {
  className?: string;
  textClassName?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <LogoMark />
      <span
        className={cn(
          "font-heading text-lg font-bold tracking-tight",
          textClassName
        )}
      >
        DevBrief
      </span>
    </span>
  );
}
