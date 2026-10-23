"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Mail, MessageCircle, QrCode, XCircle } from "lucide-react";
import { api, type EmailStatus, type WhatsAppStatus } from "@/lib/api";
import { Alert, Button, Card, CardHeader, PageHeader } from "@/components/ui";

const WAITING = ["starting", "waiting_for_qr"];

export default function ConnectionsPage() {
  const [email, setEmail] = useState<EmailStatus | null>(null);
  const [wa, setWa] = useState<WhatsAppStatus | null>(null);
  const [error, setError] = useState("");

  const loadWa = useCallback(async () => {
    try {
      setWa(await api.whatsappStatus());
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    api.emailStatus().then(setEmail).catch((e) => setError(e.message));
    loadWa();
  }, [loadWa]);

  // Keep checking while the QR code is waiting to be scanned.
  useEffect(() => {
    if (!wa || !WAITING.includes(wa.status)) return;
    const timer = setTimeout(loadWa, 2000);
    return () => clearTimeout(timer);
  }, [wa, loadWa]);

  async function connect() {
    await api.connectWhatsApp();
    setTimeout(loadWa, 500);
  }

  const waConnected = wa && (wa.status === "logged_in" || wa.status === "probably_logged_in");

  return (
    <>
      <PageHeader title="Connections" description="The accounts messages are sent from." />
      {error && (
        <div className="mb-6">
          <Alert tone="error">{error}</Alert>
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader icon={<Mail className="size-4" />} title="Email" description="SMTP or Gmail account" />
          <div className="space-y-4 p-6">
            <StatusLine
              ok={!!email?.configured}
              loading={!email}
              label={email?.configured ? email.sender ?? "" : "No email account set up"}
            />
            {!email?.configured && email && (
              <div className="space-y-2 text-sm text-slate-600">
                <p>Set it up in the <code className="rounded bg-slate-100 px-1">.env</code> file next to the app:</p>
                <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
{`SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@company.com
SMTP_PASSWORD=your app password`}
                </pre>
                <p className="text-xs text-slate-500">
                  For Gmail, create an App Password under Google Account → Security → App passwords, then restart
                  the app.
                </p>
              </div>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            icon={<MessageCircle className="size-4" />}
            title="WhatsApp"
            description="Your own number, through WhatsApp Web"
          />
          <div className="space-y-4 p-6">
            <StatusLine
              ok={!!waConnected}
              loading={!wa}
              label={
                !wa
                  ? ""
                  : waConnected
                    ? "Connected"
                    : wa.status === "starting"
                      ? "Opening browser…"
                      : wa.status === "waiting_for_qr"
                        ? "Waiting for you to scan the QR code"
                        : wa.detail || "Not connected"
              }
            />
            {wa?.status === "waiting_for_qr" && (
              <Alert tone="info">
                <p className="flex items-center gap-2 font-medium">
                  <QrCode className="size-4" /> Scan the QR code in the Chrome window
                </p>
                <p className="mt-1 text-xs">On your phone: WhatsApp → Settings → Linked devices → Link a device.</p>
              </Alert>
            )}
            <Button
              variant={waConnected ? "secondary" : "whatsapp"}
              onClick={connect}
              loading={!!wa && WAITING.includes(wa.status)}
            >
              <QrCode className="size-4" /> {waConnected ? "Reconnect" : "Connect WhatsApp"}
            </Button>
            {wa && (
              <p className="text-xs text-slate-500">
                Sends one message at a time with a {wa.delay[0]}–{wa.delay[1]} s random pause, up to {wa.daily_limit}{" "}
                per day.
              </p>
            )}
            <Alert>
              This is not an official WhatsApp service. WhatsApp may ban numbers that send many messages, especially to
              people who haven&apos;t saved the number. Start small and avoid using your main business number.
            </Alert>
          </div>
        </Card>
      </div>
    </>
  );
}

function StatusLine({ ok, loading, label }: { ok: boolean; loading: boolean; label: string }) {
  if (loading) return <p className="text-sm text-slate-400">Checking…</p>;
  return (
    <p className="flex items-center gap-2 text-sm font-medium">
      {ok ? <CheckCircle2 className="size-4 text-emerald-600" /> : <XCircle className="size-4 text-slate-400" />}
      <span className={ok ? "text-slate-900" : "text-slate-600"}>{label}</span>
    </p>
  );
}
