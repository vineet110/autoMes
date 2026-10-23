"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  FileUp,
  Mail,
  MessageCircle,
  Paperclip,
  Plus,
  Search,
  Send,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { api, type Channel, type EmailStatus, type WhatsAppStatus } from "@/lib/api";
import { Dropzone } from "./dropzone";
import { Alert, Button, Card, CardHeader, Field, cn, inputClass } from "./ui";

const RECIPIENT_FILES = ".csv,.pdf,.docx,.txt";

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function Composer() {
  const router = useRouter();
  const [channel, setChannel] = useState<Channel>("email");
  const [recipients, setRecipients] = useState<Record<Channel, string[]>>({ email: [], whatsapp: [] });
  const [importNote, setImportNote] = useState<{ added: number; files: string; problems: string[] } | null>(null);
  const [importing, setImporting] = useState(false);
  const [manual, setManual] = useState("");
  const [filter, setFilter] = useState("");

  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [cc, setCc] = useState("");
  const [attachments, setAttachments] = useState<File[]>([]);

  const [emailStatus, setEmailStatus] = useState<EmailStatus | null>(null);
  const [waStatus, setWaStatus] = useState<WhatsAppStatus | null>(null);

  const [testTo, setTestTo] = useState("");
  const [testState, setTestState] = useState<{ loading?: boolean; ok?: string; error?: string }>({});
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  // The page is pre-rendered, so inputs appear before React is ready. Keep them disabled until then,
  // otherwise text typed in that moment shows on screen but is never stored.
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);

  const whatsapp = channel === "whatsapp";
  const list = recipients[channel];

  useEffect(() => {
    api.emailStatus().then(setEmailStatus).catch(() => setEmailStatus({ configured: false, sender: null }));
    api.whatsappStatus().then(setWaStatus).catch(() => null);
  }, []);

  const switchChannel = (next: Channel) => {
    setChannel(next);
    setImportNote(null);
    setError("");
    setFilter("");
  };

  async function importFiles(files: File[], label?: string) {
    setImporting(true);
    setError("");
    try {
      const result = await api.parseRecipients(files, channel);
      const seen = new Set(list.map((r) => r.toLowerCase()));
      const added = result.emails.filter((r) => !seen.has(r.toLowerCase()));
      setRecipients((prev) => ({ ...prev, [channel]: [...prev[channel], ...added] }));
      setImportNote({
        added: added.length,
        files: label ?? result.files.map((f) => `${f.file} (${f.found})`).join(", "),
        problems: result.problems,
      });
      return added.length;
    } catch (e) {
      setError((e as Error).message);
      return 0;
    } finally {
      setImporting(false);
    }
  }

  async function addManual() {
    if (!manual.trim()) return;
    // Reuse the server's parser (same validation as uploaded files) by sending the text as a .txt file.
    const file = new File([manual], "typed.txt", { type: "text/plain" });
    await importFiles([file], "typed in");
    setManual("");
  }

  const removeRecipient = (address: string) =>
    setRecipients((prev) => ({ ...prev, [channel]: prev[channel].filter((r) => r !== address) }));

  const visible = useMemo(
    () => (filter ? list.filter((r) => r.toLowerCase().includes(filter.toLowerCase())) : list),
    [list, filter],
  );

  const totalAttachmentSize = attachments.reduce((sum, f) => sum + f.size, 0);
  const estimatedMinutes = waStatus
    ? Math.ceil((list.length * ((waStatus.delay[0] + waStatus.delay[1]) / 2 + 10)) / 60)
    : 0;

  const blockers: string[] = [];
  if (!list.length) blockers.push("Add at least one recipient");
  if (!whatsapp && !subject.trim()) blockers.push("Write a subject");
  if (!body.trim() && !(whatsapp && attachments.length)) blockers.push("Write a message");
  if (!whatsapp && emailStatus && !emailStatus.configured) blockers.push("Set up an email account");

  async function sendTest() {
    setTestState({ loading: true });
    try {
      await api.sendTest(testTo, subject, body, attachments);
      setTestState({ ok: `Test sent to ${testTo}` });
    } catch (e) {
      setTestState({ error: (e as Error).message });
    }
  }

  async function startSending() {
    setSending(true);
    setError("");
    try {
      const { job_id } = await api.createJob({ channel, recipients: list, subject, body, cc, attachments });
      router.push(`/campaigns/view/?id=${job_id}`);
    } catch (e) {
      dialogRef.current?.close();
      setError((e as Error).message);
      setSending(false);
    }
  }

  return (
    <fieldset disabled={!ready} className="min-w-0">
      {/* Channel switch */}
      <div className="mb-6 inline-flex rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
        {(
          [
            ["email", "Email", Mail],
            ["whatsapp", "WhatsApp", MessageCircle],
          ] as const
        ).map(([value, label, Icon]) => (
          <button
            key={value}
            type="button"
            onClick={() => switchChannel(value)}
            className={cn(
              "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition",
              channel === value
                ? value === "whatsapp"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "bg-brand-600 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900",
            )}
          >
            <Icon className="size-4" />
            {label}
            {recipients[value].length > 0 && (
              <span
                className={cn(
                  "rounded-full px-1.5 text-xs",
                  channel === value ? "bg-white/20" : "bg-slate-100 text-slate-600",
                )}
              >
                {recipients[value].length}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6">
          {/* Recipients */}
          <Card>
            <CardHeader
              icon={<Users className="size-4" />}
              title="Recipients"
              description={
                whatsapp
                  ? "Mobile numbers are picked up from your files. 10-digit numbers get +91."
                  : "Every email address in your files is picked up. Duplicates are removed."
              }
              action={
                list.length > 0 && (
                  <Button
                    variant="ghost"
                    className="px-2 py-1 text-xs"
                    onClick={() => setRecipients((prev) => ({ ...prev, [channel]: [] }))}
                  >
                    <Trash2 className="size-3.5" /> Clear all
                  </Button>
                )
              }
            />
            <div className="space-y-4 p-6">
              <Dropzone
                onFiles={(files) => importFiles(files)}
                accept={RECIPIENT_FILES}
                disabled={importing}
                icon={<FileUp className="size-5" />}
                title={importing ? "Reading files…" : "Drop files here or click to upload"}
                hint="CSV, PDF, Word (.docx) or TXT — you can upload several at once"
              />

              {importNote && (
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
                  <p className="flex items-center gap-2 font-medium text-slate-800">
                    <CheckCircle2 className="size-4 text-emerald-600" />
                    Added {importNote.added} new {whatsapp ? "number" : "address"}
                    {importNote.added === 1 ? "" : whatsapp ? "s" : "es"}
                    <span className="font-normal text-slate-500">from {importNote.files}</span>
                  </p>
                  {importNote.problems.length > 0 && (
                    <details className="mt-2 text-slate-600">
                      <summary className="cursor-pointer text-amber-700">
                        {importNote.problems.length} skipped — show details
                      </summary>
                      <ul className="scroll-thin mt-2 max-h-40 space-y-0.5 overflow-auto text-xs">
                        {importNote.problems.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                <input
                  className={inputClass}
                  placeholder={whatsapp ? "Type or paste numbers, e.g. 98765 43210" : "Type or paste addresses"}
                  value={manual}
                  onChange={(e) => setManual(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addManual()}
                />
                <Button variant="secondary" onClick={addManual} disabled={!manual.trim() || importing}>
                  <Plus className="size-4" /> Add
                </Button>
              </div>

              {list.length > 0 && (
                <div className="overflow-hidden rounded-xl border border-slate-200">
                  <div className="flex items-center gap-3 border-b border-slate-100 bg-slate-50 px-4 py-2">
                    <span className="text-sm font-medium text-slate-700">
                      {list.length} recipient{list.length === 1 ? "" : "s"}
                    </span>
                    {list.length > 8 && (
                      <div className="relative ml-auto w-48">
                        <Search className="absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-slate-400" />
                        <input
                          className={cn(inputClass, "py-1 pl-8 text-xs")}
                          placeholder="Search"
                          value={filter}
                          onChange={(e) => setFilter(e.target.value)}
                        />
                      </div>
                    )}
                  </div>
                  <ul className="scroll-thin max-h-72 divide-y divide-slate-100 overflow-auto">
                    {visible.map((r) => (
                      <li key={r} className="group flex items-center justify-between px-4 py-1.5 text-sm">
                        <span className="truncate text-[13px] text-slate-700">{r}</span>
                        <button
                          type="button"
                          onClick={() => removeRecipient(r)}
                          className="rounded p-1 text-slate-400 opacity-0 group-hover:opacity-100 hover:bg-slate-100 hover:text-red-600 focus:opacity-100"
                          aria-label={`Remove ${r}`}
                        >
                          <X className="size-3.5" />
                        </button>
                      </li>
                    ))}
                    {!visible.length && <li className="px-4 py-3 text-sm text-slate-500">No match</li>}
                  </ul>
                </div>
              )}
            </div>
          </Card>

          {/* Message */}
          <Card>
            <CardHeader
              icon={whatsapp ? <MessageCircle className="size-4" /> : <Mail className="size-4" />}
              title="Message"
              description={
                whatsapp ? "Sent as a normal WhatsApp chat message." : "Plain-text email, sent from your account."
              }
            />
            <div className="space-y-5 p-6">
              {!whatsapp && (
                <Field label="Subject" htmlFor="subject">
                  <input id="subject" className={inputClass} value={subject} onChange={(e) => setSubject(e.target.value)} />
                </Field>
              )}
              <Field label="Message" htmlFor="body">
                <textarea
                  id="body"
                  rows={10}
                  className={cn(inputClass, "resize-y leading-relaxed")}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder={whatsapp ? "Hello! …" : "Dear Sir/Madam, …"}
                />
              </Field>
              {!whatsapp && (
                <Field label="CC" htmlFor="cc" hint="Optional. Added to every email — separate several with commas.">
                  <input id="cc" className={inputClass} value={cc} onChange={(e) => setCc(e.target.value)} />
                </Field>
              )}

              <div className="space-y-2">
                <span className="block text-sm font-medium text-slate-700">Attachments</span>
                <Dropzone
                  compact
                  onFiles={(files) => setAttachments((prev) => [...prev, ...files])}
                  icon={<Paperclip className="size-4" />}
                  title="Attach files"
                  hint="Optional — sent to every recipient"
                />
                {attachments.length > 0 && (
                  <ul className="flex flex-wrap gap-2">
                    {attachments.map((f, i) => (
                      <li
                        key={`${f.name}-${i}`}
                        className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white py-1 pr-1 pl-3 text-sm shadow-sm"
                      >
                        <Paperclip className="size-3.5 text-slate-400" />
                        <span className="max-w-48 truncate">{f.name}</span>
                        <span className="text-xs text-slate-400">{formatBytes(f.size)}</span>
                        <button
                          type="button"
                          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-red-600"
                          onClick={() => setAttachments((prev) => prev.filter((_, j) => j !== i))}
                          aria-label={`Remove ${f.name}`}
                        >
                          <X className="size-3.5" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {!whatsapp && (
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="mb-2 text-sm font-medium text-slate-700">Send yourself a test first</p>
                  <div className="flex flex-wrap gap-2">
                    <input
                      type="email"
                      className={cn(inputClass, "min-w-56 flex-1")}
                      placeholder="you@company.com"
                      value={testTo}
                      onChange={(e) => setTestTo(e.target.value)}
                    />
                    <Button
                      variant="secondary"
                      onClick={sendTest}
                      loading={testState.loading}
                      disabled={!testTo || !subject.trim() || !body.trim()}
                    >
                      Send test
                    </Button>
                  </div>
                  {testState.ok && <p className="mt-2 text-sm text-emerald-700">{testState.ok}</p>}
                  {testState.error && <p className="mt-2 text-sm text-red-600">{testState.error}</p>}
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Summary */}
        <div className="space-y-4 lg:sticky lg:top-10 lg:self-start">
          <Card>
            <div className="space-y-4 p-5">
              <h2 className="text-[15px] font-semibold">Summary</h2>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Recipients</dt>
                  <dd className="font-medium">{list.length}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Attachments</dt>
                  <dd className="font-medium">
                    {attachments.length ? `${attachments.length} · ${formatBytes(totalAttachmentSize)}` : "None"}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="shrink-0 text-slate-500">Sending from</dt>
                  <dd className="truncate text-right font-medium">
                    {whatsapp ? (
                      <WhatsAppConnection status={waStatus} />
                    ) : emailStatus?.configured ? (
                      <span title={emailStatus.sender ?? ""}>{emailStatus.sender?.split(" as ").pop()}</span>
                    ) : (
                      <Link href="/connections/" className="text-red-600 underline">
                        Not set up
                      </Link>
                    )}
                  </dd>
                </div>
                {whatsapp && list.length > 0 && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Estimated time</dt>
                    <dd className="font-medium">~{estimatedMinutes} min</dd>
                  </div>
                )}
              </dl>

              {error && <Alert tone="error">{error}</Alert>}

              <Button
                variant={whatsapp ? "whatsapp" : "primary"}
                className="w-full py-2.5"
                disabled={blockers.length > 0}
                onClick={() => dialogRef.current?.showModal()}
              >
                <Send className="size-4" /> Review & send
              </Button>
              {blockers.length > 0 && (
                <ul className="space-y-1 text-xs text-slate-500">
                  {blockers.map((b) => (
                    <li key={b}>• {b}</li>
                  ))}
                </ul>
              )}
            </div>
          </Card>

          {whatsapp && (
            <Alert>
              <p className="flex items-center gap-2 font-medium">
                <AlertTriangle className="size-4" /> Use with care
              </p>
              <p className="mt-1 text-xs leading-relaxed">
                Messages go from your own number through WhatsApp Web, one at a time with a random pause. WhatsApp may
                ban numbers that message many people who haven&apos;t saved them. Limit:{" "}
                {waStatus?.daily_limit ?? 150}/day.
              </p>
            </Alert>
          )}

          <MessagePreview channel={channel} subject={subject} body={body} attachments={attachments} />
        </div>
      </div>

      {/* Confirmation */}
      <dialog
        ref={dialogRef}
        className="m-auto w-[calc(100%-2rem)] max-w-lg rounded-2xl border border-slate-200 p-0 shadow-xl"
      >
        <div className="p-6">
          <h2 className="text-lg font-semibold">Send {list.length} {whatsapp ? "WhatsApp messages" : "emails"}?</h2>
          <p className="mt-1 text-sm text-slate-500">
            Each person gets their own separate message — nobody sees anyone else&apos;s{" "}
            {whatsapp ? "number" : "address"}.
          </p>
          <dl className="mt-5 space-y-2 rounded-xl bg-slate-50 p-4 text-sm">
            {!whatsapp && (
              <>
                <Row label="Subject" value={subject} />
                {cc && <Row label="CC" value={cc} />}
              </>
            )}
            <Row label="First recipients" value={list.slice(0, 3).join(", ") + (list.length > 3 ? ", …" : "")} />
            <Row label="Attachments" value={attachments.map((f) => f.name).join(", ") || "None"} />
            {whatsapp && <Row label="Estimated time" value={`about ${estimatedMinutes} minutes`} />}
          </dl>
          {whatsapp && (
            <p className="mt-3 text-xs text-slate-500">
              A Chrome window will open and send the messages. Keep it open and the computer awake until it finishes.
            </p>
          )}
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-100 bg-slate-50/60 px-6 py-4">
          <Button variant="secondary" onClick={() => dialogRef.current?.close()} disabled={sending}>
            Back
          </Button>
          <Button variant={whatsapp ? "whatsapp" : "primary"} onClick={startSending} loading={sending}>
            Send now
          </Button>
        </div>
      </dialog>
    </fieldset>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-3">
      <dt className="text-slate-500">{label}</dt>
      <dd className="break-words text-slate-800">{value}</dd>
    </div>
  );
}

function WhatsAppConnection({ status }: { status: WhatsAppStatus | null }) {
  if (!status) return <span className="text-slate-400">…</span>;
  if (status.status === "logged_in" || status.status === "probably_logged_in")
    return <span className="text-emerald-700">Your WhatsApp</span>;
  return (
    <Link href="/connections/" className="text-red-600 underline">
      Connect WhatsApp
    </Link>
  );
}

function MessagePreview({
  channel,
  subject,
  body,
  attachments,
}: {
  channel: Channel;
  subject: string;
  body: string;
  attachments: File[];
}) {
  if (!body.trim() && !subject.trim()) return null;
  if (channel === "whatsapp") {
    return (
      <Card className="overflow-hidden">
        <p className="border-b border-slate-100 px-5 py-3 text-xs font-medium tracking-wide text-slate-500 uppercase">
          Preview
        </p>
        <div className="bg-[#efeae2] p-4">
          {attachments.map((f, i) => (
            <div key={i} className="mb-2 ml-auto w-fit max-w-[85%] rounded-lg bg-[#d9fdd3] px-3 py-2 text-sm shadow-sm">
              <Paperclip className="mr-1 inline size-3.5" />
              {f.name}
            </div>
          ))}
          {body.trim() && (
            <div className="ml-auto w-fit max-w-[85%] rounded-lg rounded-tr-none bg-[#d9fdd3] px-3 py-2 text-sm whitespace-pre-wrap text-slate-900 shadow-sm">
              {body}
              <span className="ml-2 align-bottom text-[10px] text-slate-500">now ✓✓</span>
            </div>
          )}
        </div>
      </Card>
    );
  }
  return (
    <Card className="overflow-hidden">
      <p className="border-b border-slate-100 px-5 py-3 text-xs font-medium tracking-wide text-slate-500 uppercase">
        Preview
      </p>
      <div className="space-y-2 p-5 text-sm">
        <p className="font-semibold text-slate-900">{subject || "(no subject)"}</p>
        <p className="scroll-thin max-h-64 overflow-auto whitespace-pre-wrap text-slate-700">{body}</p>
        {attachments.length > 0 && (
          <p className="text-xs text-slate-500">
            <Paperclip className="mr-1 inline size-3" />
            {attachments.length} attachment{attachments.length === 1 ? "" : "s"}
          </p>
        )}
      </div>
    </Card>
  );
}
