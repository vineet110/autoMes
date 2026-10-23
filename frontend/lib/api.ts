export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export type Channel = "email" | "whatsapp";
export type JobStatus = "pending" | "running" | "completed" | "cancelled" | "error";
export type RecipientStatus = "pending" | "sent" | "failed";

export interface Counts {
  pending: number;
  sent: number;
  failed: number;
  total: number;
}

export interface Job {
  id: number;
  created_at: string;
  channel: Channel;
  subject: string;
  body: string;
  cc: string[];
  status: JobStatus;
  error: string | null;
  counts: Counts;
  attachments: string[];
  recipients?: { address: string; status: RecipientStatus; error: string | null; sent_at: string | null }[];
}

export interface ParseResult {
  emails: string[];
  problems: string[];
  files: { file: string; found: number }[];
}

export interface EmailStatus {
  configured: boolean;
  sender: string | null;
}

export interface WhatsAppStatus {
  status: string;
  detail: string;
  daily_limit: number;
  delay: [number, number];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return data as T;
}

const post = <T>(path: string, body?: FormData) => request<T>(path, { method: "POST", body });

export const api = {
  emailStatus: () => request<EmailStatus>("/api/status"),
  whatsappStatus: () => request<WhatsAppStatus>("/api/whatsapp/status"),
  connectWhatsApp: () => post<{ ok: boolean }>("/api/whatsapp/login"),

  parseRecipients(files: File[], channel: Channel) {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    form.append("channel", channel);
    return post<ParseResult>("/api/recipients/parse", form);
  },

  sendTest(to: string, subject: string, body: string, attachments: File[]) {
    const form = new FormData();
    form.append("to", to);
    form.append("subject", subject);
    form.append("body", body);
    attachments.forEach((f) => form.append("attachments", f));
    return post<{ ok: boolean }>("/api/send-test", form);
  },

  createJob(input: {
    channel: Channel;
    recipients: string[];
    subject: string;
    body: string;
    cc: string;
    attachments: File[];
  }) {
    const form = new FormData();
    form.append("channel", input.channel);
    form.append("recipients", input.recipients.join("\n"));
    form.append("subject", input.subject);
    form.append("body", input.body);
    form.append("cc", input.cc);
    input.attachments.forEach((f) => form.append("attachments", f));
    return post<{ job_id: number }>("/api/jobs", form);
  },

  listJobs: () => request<Job[]>("/api/jobs"),
  getJob: (id: number) => request<Job>(`/api/jobs/${id}`),
  retryJob: (id: number) => post<{ ok: boolean }>(`/api/jobs/${id}/retry`),
  cancelJob: (id: number) => post<{ ok: boolean }>(`/api/jobs/${id}/cancel`),
};

export function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
