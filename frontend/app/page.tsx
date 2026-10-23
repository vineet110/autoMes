import { Composer } from "@/components/composer";
import { PageHeader } from "@/components/ui";

export default function NewCampaignPage() {
  return (
    <>
      <PageHeader
        title="New campaign"
        description="Upload your list, write one message, and it goes to every person individually."
      />
      <Composer />
    </>
  );
}
