"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { History, PlugZap, Send } from "lucide-react";
import { cn } from "./ui";

const links = [
  { href: "/", label: "New campaign", icon: Send },
  { href: "/campaigns/", label: "Campaigns", icon: History },
  { href: "/connections/", label: "Connections", icon: PlugZap },
];

export function Sidebar() {
  const pathname = usePathname();
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href.replace(/\/$/, ""));

  return (
    <aside className="sticky top-0 z-10 flex shrink-0 items-center gap-6 border-b border-slate-200 bg-white px-4 py-3 md:h-screen md:w-60 md:self-start md:flex-col md:items-stretch md:border-r md:border-b-0 md:px-3 md:py-5">
      <Link href="/" className="flex items-center gap-2.5 md:px-3 md:pb-6">
        <span className="grid size-8 place-items-center rounded-lg bg-brand-600 text-white shadow-sm">
          <Send className="size-4" />
        </span>
        <span className="font-semibold tracking-tight text-slate-900">AutoMailer</span>
      </Link>
      <nav className="flex gap-1 overflow-x-auto md:flex-col">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap transition",
              isActive(href) ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
            )}
          >
            <Icon className="size-4" />
            <span className="hidden sm:inline">{label}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
