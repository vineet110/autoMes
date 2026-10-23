"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Inbox, Plus } from "lucide-react";
import { api, formatDate, type Job } from "@/lib/api";
import { Alert, Button, Card, ChannelBadge, PageHeader, Progress, StatusBadge } from "@/components/ui";

export default function CampaignsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const data = await api.listJobs();
        setJobs(data);
        if (data.some((j) => j.status === "running")) timer = setTimeout(load, 3000);
      } catch (e) {
        setError((e as Error).message);
      }
    };
    load();
    return () => clearTimeout(timer);
  }, []);

  return (
    <>
      <PageHeader
        title="Campaigns"
        description="Everything you have sent, newest first."
        action={
          <Link href="/">
            <Button>
              <Plus className="size-4" /> New campaign
            </Button>
          </Link>
        }
      />
      {error && <Alert tone="error">{error}</Alert>}
      {jobs && jobs.length === 0 && (
        <Card className="flex flex-col items-center px-6 py-16 text-center">
          <Inbox className="size-10 text-slate-300" />
          <p className="mt-3 font-medium">No campaigns yet</p>
          <p className="mt-1 text-sm text-slate-500">Your sent campaigns will show up here.</p>
        </Card>
      )}
      {jobs && jobs.length > 0 && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-100 bg-slate-50 text-left text-xs font-medium text-slate-500 uppercase">
                <tr>
                  <th className="px-5 py-3">Campaign</th>
                  <th className="px-5 py-3">Channel</th>
                  <th className="px-5 py-3">Progress</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    onClick={() => router.push(`/campaigns/view/?id=${job.id}`)}
                    className="cursor-pointer transition hover:bg-slate-50"
                  >
                    <td className="max-w-72 px-5 py-3.5">
                      <p className="truncate font-medium text-slate-900">{job.subject}</p>
                      <p className="text-xs text-slate-500">#{job.id}</p>
                    </td>
                    <td className="px-5 py-3.5">
                      <ChannelBadge channel={job.channel} />
                    </td>
                    <td className="min-w-44 px-5 py-3.5">
                      <Progress {...job.counts} />
                      <p className="mt-1 text-xs text-slate-500">
                        {job.counts.sent}/{job.counts.total} sent
                        {job.counts.failed > 0 && <span className="text-red-600"> · {job.counts.failed} failed</span>}
                      </p>
                    </td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap text-slate-500">{formatDate(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}
