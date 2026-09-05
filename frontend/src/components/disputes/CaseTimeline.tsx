import React from 'react';
import { Card } from '../common/Card';
import { DisputeTimelineEvent } from '../../types/dispute';
import { formatDate } from '../../utils/formatters';

interface CaseTimelineProps {
  auditTrail: DisputeTimelineEvent[];
}

export const CaseTimeline: React.FC<CaseTimelineProps> = ({ auditTrail }) => {
  // Format event title for merchant readability
  const formatEventTitle = (title: string, eventType: string): string => {
    if (eventType === 'SYSTEM_CREATED' || title.toLowerCase().includes('created')) {
      return 'Dispute Received';
    }
    if (eventType === 'EVIDENCE_ADDED' || title.toLowerCase().includes('evidence')) {
      return 'Evidence Attached';
    }
    if (eventType === 'SUBMITTED' || title.toLowerCase().includes('submit')) {
      return 'Merchant Response Submitted';
    }
    if (eventType === 'MERCHANT_ACCEPTED') {
      return 'Dispute Accepted (Concession)';
    }
    if (eventType === 'MERCHANT_OVERRIDE') {
      return 'Recommendation Strategy Updated';
    }
    return title.replace(/_/g, ' ');
  };

  return (
    <section id="case-timeline" className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 tracking-tight">Case Timeline & Audit Trail</h2>
        <span className="text-xs text-slate-500">Immutable chronological milestone history</span>
      </div>

      <Card className="p-6 border-slate-200">
        {auditTrail.length === 0 ? (
          <p className="text-xs text-slate-500">No timeline events recorded yet.</p>
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {auditTrail.map((evt, idx) => (
              <div key={evt.event_id || idx} className="relative group">
                {/* Checkpoint Dot */}
                <div className="absolute -left-6 top-1 w-3 h-3 rounded-full bg-indigo-600 border-2 border-white ring-2 ring-indigo-100" />

                <div className="space-y-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="text-xs font-bold text-slate-900">
                      {formatEventTitle(evt.title, evt.event_type)}
                    </h4>
                    <span className="text-[11px] text-slate-400 font-mono">
                      {formatDate(evt.timestamp)}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 leading-relaxed">
                    {evt.description || 'Milestone logged in case repository.'}
                  </p>

                  {evt.actor_type && (
                    <span className="inline-block text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded font-mono">
                      Actor: {evt.actor_type}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </section>
  );
};
