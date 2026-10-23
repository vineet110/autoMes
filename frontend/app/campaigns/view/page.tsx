import { Suspense } from "react";
import { CampaignDetail } from "@/components/campaign-detail";

// The campaign id comes from ?id=…, which is only known in the browser (static export).
export default function CampaignPage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
      <CampaignDetail />
    </Suspense>
  );
}
