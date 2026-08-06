import { Database, FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CORPUS = [
  { name: "Federal statutes (U.S.C.)", type: "Statutes", status: "Ongoing ingestion" },
  { name: "Supreme Court opinions", type: "Case law", status: "Ongoing ingestion" },
  { name: "Federal regulations (C.F.R.)", type: "Regulations", status: "Planned" },
  { name: "State codes (selected jurisdictions)", type: "Statutes", status: "Planned" },
  { name: "Model rules & practice guides", type: "Secondary sources", status: "Planned" },
];

export default function SourcesPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center gap-2">
        <Database className="h-6 w-6 text-primary" />
        <h1 className="text-3xl font-bold">Data sources</h1>
      </div>
      <p className="mt-2 text-muted-foreground">
        The corpus Legisight retrieves from. Documents are ingested from the server-side raw
        document directory and indexed as vector embeddings.
      </p>

      <div className="mt-8 space-y-4">
        {CORPUS.map((item) => (
          <Card key={item.name}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4 text-primary" />
                {item.name}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                <span className="font-medium text-foreground">{item.type}</span> · {item.status}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
