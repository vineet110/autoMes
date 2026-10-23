"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, Paperclip, RotateCw, Search, Square } from "lucide-react";
import { api, formatDate, type Job, type RecipientStatus } from "@/lib/api";
import { Alert, Button, Card, ChannelBadge, Progress, StatusBadge, cn, inputClass } from "./ui";

type Filter = "all" | RecipientStatus;

export function CampaignDetail() {
  const id = Number(useSearchParams().get("id"));
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setJob(await api.getJob(id));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    if (id) load();
  }, [id, load]);

  // Poll while sending.
  useEffect(() => {
    if (job?.status !== "running") return;
    const timer = setTimeout(load, 2000);
    return () => clearTimeout(timer);
  }, [job, load]);

  const rows = useMemo(() => {
    const all = job?.recipients ?? [];
    return all.filter(
      (r) => (filter === "all" || r.status === filter) && (!query || r.address.toLowerCase().includes(query.toLowerCase())),
    );
  }, [job, filter, query]);

  async function act(action: "retry" | "cancel") {
    setBusy(true);
    try {
      await (action === "retry" ? api.retryJob(id) : api.cancelJob(id));
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!id) return <Alert tone="error">No campaign selected.</Alert>;
  if (!job) return error ? <Alert tone="error">{error}</Alert> : <p className="text-sm text-slate-500">Loading…</p>;

  const { counts } = job;
  const done = counts.sent + counts.failed;
  const canResume = job.status !== "running" && (counts.failed > 0 || counts.pending > 0);

  return (
    <>
      <Link href="/campaigns/" className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900">
        <ArrowLeft className="size-4" /> All campaigns
      </Link>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <ChannelBadge channel={job.channel} />
            <StatusBadge status={job.status} />
          </div>
          <h1 className="mt-2 truncate text-2xl font-semibold tracking-tight">{job.subject}</h1>
          <p className="mt-1 text-sm text-slate-500">
            Campaign #{job.id} · started {formatDate(job.created_at)}
          </p>
        </div>
        <div className="flex gap-2">
          {job.status === "running" && (
            <Button variant="danger" onClick={() => act("cancel")} loading={busy}>
              <Square className="size-3.5" /> Stop
            </Button>
          )}
          {canResume && (
            <Button variant="secondary" onClick={() => act("retry")} loading={busy}>
              <RotateCw className="size-4" />
              {counts.failed > 0 ? `Retry ${counts.failed} failed` : "Resume"}
              {counts.failed > 0 && counts.pending > 0 && " & resume"}
            </Button>
          )}
        </div>
      </div>

      {job.error && (
        <div className="mb-6">
          <Alert tone={job.status === "error" ? "error" : "warning"}>{job.error}</Alert>
        </div>
      )}
      {error && (
        <div className="mb-6">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Total" value={counts.total} />
        <Stat label="Sent" value={counts.sent} tone="text-emerald-600" />
        <Stat label="Failed" value={counts.failed} tone="text-red-600" />
        <Stat label="Waiting" value={counts.pending} tone="text-slate-500" />
      </div>

      <Card className="mb-6 p-5">
        <div className="mb-2 flex justify-between text-sm">
          <span className="font-medium">Progress</span>
          <span className="text-slate-500">
            {done} of {counts.total} · {counts.total ? Math.round((done / counts.total) * 100) : 0}%
          </span>
        </div>
        <Progress {...counts} className="h-2.5" />
      </Card>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 px-5 py-3">
            <div className="flex rounded-lg bg-slate-100 p-0.5 text-sm">
              {(["all", "sent", "failed", "pending"] as Filter[]).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
                  className={cn(
                    "rounded-md px-3 py-1 font-medium capitalize transition",
                    filter === f ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-800",
                  )}
                >
                  {f === "pending" ? "waiting" : f}
                </button>
              ))}
            </div>
            <div className="relative ml-auto w-full sm:w-52">
              <Search className="absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-slate-400" />
              <input
                className={cn(inputClass, "py-1.5 pl-8")}
                placeholder="Search recipients"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>
          <div className="scroll-thin max-h-[560px] overflow-auto">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-slate-100">
                {rows.map((r) => (
                  <tr key={r.address}>
                    <td className="px-5 py-2.5 text-[13px] text-slate-800">
                      <p className="break-all">{r.address}</p>
                      {/* On phones the detail column is hidden, so show it under the address. */}
                      {(r.error || r.sent_at) && (
                        <p className={cn("mt-0.5 text-xs sm:hidden", r.error ? "text-red-600" : "text-slate-500")}>
                          {r.error ?? formatDate(r.sent_at!)}
                        </p>
                      )}
                    </td>
                    <td className="px-5 py-2.5">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className={cn("hidden px-5 py-2.5 text-xs sm:table-cell", r.error ? "text-red-600" : "text-slate-500")}>
                      {r.error ?? (r.sent_at ? formatDate(r.sent_at) : "")}
                    </td>
                  </tr>
                ))}
                {!rows.length && (
                  <tr>
                    <td className="px-5 py-8 text-center text-slate-500">Nothing here</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <Card className="self-start">
          <p className="border-b border-slate-100 px-5 py-3 text-xs font-medium tracking-wide text-slate-500 uppercase">
            Message
          </p>
          <div className="space-y-3 p-5 text-sm">
            {job.cc.length > 0 && (
              <p>
                <span className="text-slate-500">CC: </span>
                {job.cc.join(", ")}
              </p>
            )}
            <p className="scroll-thin max-h-80 overflow-auto whitespace-pre-wrap text-slate-700">{job.body}</p>
            {job.attachments.length > 0 && (
              <ul className="space-y-1 border-t border-slate-100 pt-3">
                {job.attachments.map((a) => (
                  <li key={a} className="flex items-center gap-2 text-slate-600">
                    <Paperclip className="size-3.5" /> {a}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>
      </div>
    </>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <Card className="px-5 py-4">
      <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">{label}</p>
      <p className={cn("mt-1 text-2xl font-semibold tabular-nums", tone)}>{value}</p>
    </Card>
  );
}
