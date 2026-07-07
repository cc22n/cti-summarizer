import { useState } from "react";
import { CheckCircle, Circle, Save } from "lucide-react";
import type { Alert } from "../../types/alert";
import SeverityBadge from "../common/SeverityBadge";
import { formatDateTime, formatCVSS } from "../../lib/formatters";
import { useAcknowledgeAlert, useUpdateNotes } from "../../hooks/useAlerts";

interface Props {
  alert: Alert;
}

function JsonBlock({ data }: { data: Record<string, unknown> | null }) {
  if (!data) return <span className="text-gray-600">—</span>;
  return (
    <pre className="text-xs text-gray-300 bg-gray-900 rounded p-3 overflow-auto max-h-40 whitespace-pre-wrap">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

export default function AlertDetailCard({ alert }: Props) {
  const ack = useAcknowledgeAlert();
  const updateNotes = useUpdateNotes();
  const [notes, setNotes] = useState(alert.notes ?? "");
  const notesDirty = notes !== (alert.notes ?? "");

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-800 flex items-start gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <SeverityBadge severity={alert.severity} />
            <span className="text-xs text-gray-500">{alert.source_name}</span>
            {alert.cvss_score && (
              <span className="text-xs font-mono bg-gray-800 text-gray-300 px-2 py-0.5 rounded">
                CVSS {formatCVSS(alert.cvss_score)}
              </span>
            )}
          </div>
          <h2 className="text-lg font-semibold text-white">{alert.title}</h2>
          <p className="text-xs text-gray-500 mt-1">
            Published: {formatDateTime(alert.published_date)} &nbsp;·&nbsp;
            Ingested: {formatDateTime(alert.normalized_at)}
          </p>
        </div>

        {/* Acknowledge button */}
        <button
          onClick={() => ack.mutate(alert.id)}
          disabled={ack.isPending}
          title={alert.is_acknowledged ? "Mark as unacknowledged" : "Mark as acknowledged"}
          className={`flex items-center gap-1.5 text-xs rounded-md px-3 py-1.5 border transition-colors ${
            alert.is_acknowledged
              ? "border-green-600/40 bg-green-900/20 text-green-400 hover:bg-green-900/40"
              : "border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500"
          }`}
        >
          {alert.is_acknowledged ? (
            <CheckCircle className="h-3.5 w-3.5" />
          ) : (
            <Circle className="h-3.5 w-3.5" />
          )}
          {alert.is_acknowledged ? "Acknowledged" : "Acknowledge"}
        </button>
      </div>

      {/* Body */}
      <div className="px-6 py-4 grid gap-5">
        {alert.description && (
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              Description
            </p>
            <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
              {alert.description}
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              Affected Products
            </p>
            <JsonBlock data={alert.affected_products} />
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              Attack Vectors
            </p>
            <JsonBlock data={alert.attack_vectors} />
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              MITRE Techniques
            </p>
            <JsonBlock data={alert.mitre_techniques} />
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              IOCs
            </p>
            <JsonBlock data={alert.iocs} />
          </div>
        </div>

        {alert.categories.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              Categories
            </p>
            <div className="flex flex-wrap gap-2">
              {alert.categories.map((c) => (
                <span
                  key={c.id}
                  className="text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded"
                >
                  {c.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Analyst Notes */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Analyst Notes
            </p>
            {notesDirty && (
              <button
                onClick={() => updateNotes.mutate({ id: alert.id, notes: notes || null })}
                disabled={updateNotes.isPending}
                className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                <Save className="h-3 w-3" />
                {updateNotes.isPending ? "Saving…" : "Save"}
              </button>
            )}
          </div>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add investigation notes…"
            rows={4}
            className="w-full bg-gray-900 border border-gray-700 text-gray-300 text-sm rounded-md px-3 py-2 resize-none focus:outline-none focus:border-blue-500 placeholder-gray-600"
          />
        </div>
      </div>
    </div>
  );
}
