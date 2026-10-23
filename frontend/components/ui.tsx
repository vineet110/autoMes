import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import type { Channel, JobStatus } from "@/lib/api";

export function cn(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section className={cn("rounded-2xl border border-slate-200 bg-white shadow-sm", className)}>{children}</section>
  );
}

export function CardHeader({
  title,
  description,
  icon,
  action,
}: {
  title: string;
  description?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 border-b border-slate-100 px-6 py-4">
      {icon && <div className="mt-0.5 rounded-lg bg-slate-100 p-2 text-slate-600">{icon}</div>}
      <div className="min-w-0 flex-1">
        <h2 className="text-[15px] font-semibold text-slate-900">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}

type Variant = "primary" | "secondary" | "ghost" | "danger" | "whatsapp";

const variants: Record<Variant, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 shadow-sm",
  whatsapp: "bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm",
  secondary: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 shadow-sm",
  ghost: "text-slate-600 hover:bg-slate-100",
  danger: "border border-red-200 bg-white text-red-600 hover:bg-red-50",
};

export function Button({
  variant = "primary",
  loading,
  className,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin" />}
      {children}
    </button>
  );
}

export const inputClass =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm " +
  "placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none";

export function Field({ label, hint, htmlFor, children }: { label: string; hint?: string; htmlFor?: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      {children}
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

const statusStyles: Record<string, string> = {
  running: "bg-blue-50 text-blue-700 ring-blue-200",
  completed: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  sent: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  failed: "bg-red-50 text-red-700 ring-red-200",
  error: "bg-red-50 text-red-700 ring-red-200",
  cancelled: "bg-amber-50 text-amber-700 ring-amber-200",
  pending: "bg-slate-100 text-slate-600 ring-slate-200",
};

const statusLabels: Record<string, string> = {
  running: "Sending",
  completed: "Completed",
  cancelled: "Stopped",
  error: "Paused",
  pending: "Waiting",
  sent: "Sent",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: JobStatus | string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        statusStyles[status] ?? statusStyles.pending,
      )}
    >
      {status === "running" && <span className="size-1.5 animate-pulse rounded-full bg-blue-500" />}
      {statusLabels[status] ?? status}
    </span>
  );
}

export function ChannelBadge({ channel }: { channel: Channel }) {
  return channel === "whatsapp" ? (
    <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
      WhatsApp
    </span>
  ) : (
    <span className="inline-flex items-center rounded-md bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
      Email
    </span>
  );
}

export function Progress({ sent, failed, total, className }: { sent: number; failed: number; total: number; className?: string }) {
  const pct = (n: number) => (total ? (n / total) * 100 : 0);
  return (
    <div className={cn("flex h-2 overflow-hidden rounded-full bg-slate-100", className)}>
      <div className="bg-emerald-500 transition-all duration-500" style={{ width: `${pct(sent)}%` }} />
      <div className="bg-red-400 transition-all duration-500" style={{ width: `${pct(failed)}%` }} />
    </div>
  );
}

export function Alert({ tone = "warning", children }: { tone?: "warning" | "error" | "info"; children: ReactNode }) {
  const tones = {
    warning: "border-amber-200 bg-amber-50 text-amber-900",
    error: "border-red-200 bg-red-50 text-red-800",
    info: "border-slate-200 bg-slate-50 text-slate-700",
  };
  return <div className={cn("rounded-xl border px-4 py-3 text-sm", tones[tone])}>{children}</div>;
}

export function PageHeader({ title, description, action }: { title: string; description?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}
