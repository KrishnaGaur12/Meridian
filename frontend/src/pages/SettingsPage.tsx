import React, { useState } from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';

export const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'profile' | 'account' | 'evidence' | 'integrations'>('profile');
  const [savedToast, setSavedToast] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedToast(true);
    setTimeout(() => setSavedToast(false), 3000);
  };

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="pb-1 border-b border-slate-200/60">
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Settings</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Configure merchant profile, dispute preferences, and evidence policies
        </p>
      </div>

      {savedToast && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold rounded-lg animate-in fade-in duration-150">
          Settings saved successfully.
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-1 overflow-x-auto">
        {[
          { id: 'profile', label: 'Merchant Profile' },
          { id: 'account', label: 'Account Settings' },
          { id: 'evidence', label: 'Information & Evidence' },
          { id: 'integrations', label: 'Integrations' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 text-xs font-semibold border-b-2 transition whitespace-nowrap cursor-pointer ${
              activeTab === tab.id
                ? 'border-indigo-600 text-indigo-600 font-bold bg-indigo-50/20'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-100/60'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <form onSubmit={handleSave}>
        {activeTab === 'profile' && (
          <Card className="p-5 space-y-5 bg-white">
            <div className="space-y-3.5">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Merchant Information</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  General business profile data used in chargeback defense packages.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Merchant Business Name</label>
                  <input
                    type="text"
                    defaultValue="Acme Store"
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 text-slate-900 font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Merchant ID (Razorpay MID)</label>
                  <input
                    type="text"
                    readOnly
                    defaultValue="MERCHANT_001"
                    className="w-full text-xs bg-slate-100 border border-slate-200 text-slate-500 rounded-lg p-2.5 cursor-not-allowed font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Support Email</label>
                  <input
                    type="email"
                    defaultValue="disputes@acmestore.com"
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Business Category</label>
                  <input
                    type="text"
                    defaultValue="Retail & E-commerce"
                    className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 text-slate-900"
                  />
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
              <span className="text-[11px] text-slate-400">All changes take effect immediately on next dispute package generation.</span>
              <Button type="submit" variant="primary" size="sm" className="font-semibold">
                Save Profile
              </Button>
            </div>
          </Card>
        )}

        {activeTab === 'account' && (
          <Card className="p-5 space-y-5 bg-white">
            <div className="space-y-3.5">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Dispute Operations Preferences</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Configure automation parameters for incoming chargebacks.
                </p>
              </div>

              <div className="space-y-2.5 text-xs bg-slate-50/60 p-3.5 rounded-xl border border-slate-200/80">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input type="checkbox" defaultChecked className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                  <div>
                    <span className="font-medium text-slate-900 block">Automatic AI Autopilot Evidence Extraction</span>
                    <span className="text-slate-500 text-[11px]">Automatically extract transaction receipts, payment authorization logs, and fulfillment tracking.</span>
                  </div>
                </label>
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input type="checkbox" defaultChecked className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                  <div>
                    <span className="font-medium text-slate-900 block">Urgent Deadline Alerts</span>
                    <span className="text-slate-500 text-[11px]">Highlight cases in the operational queue with URGENT priority when response window is &le; 48h.</span>
                  </div>
                </label>
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input type="checkbox" defaultChecked className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                  <div>
                    <span className="font-medium text-slate-900 block">Human-in-the-Loop Approval Gate</span>
                    <span className="text-slate-500 text-[11px]">Require explicit merchant review and confirmation before final submission to Razorpay.</span>
                  </div>
                </label>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <Button type="submit" variant="primary" size="sm" className="font-semibold">
                Save Preferences
              </Button>
            </div>
          </Card>
        )}

        {activeTab === 'evidence' && (
          <Card className="p-5 space-y-5 bg-white">
            <div className="space-y-3.5">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Standard Policy & Documents</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Preconfigured terms to be attached as evidence in chargeback rebuttal packages.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Standard Refund & Cancellation Policy</label>
                <textarea
                  rows={4}
                  defaultValue="Customers may request returns within 7 days of verified courier delivery. Digital goods are non-refundable once activated. In-store returns are processed within 3 business days."
                  className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2.5 focus:bg-white focus:ring-2 focus:ring-indigo-500/20 text-slate-800 leading-relaxed"
                />
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <Button type="submit" variant="primary" size="sm" className="font-semibold">
                Save Policies
              </Button>
            </div>
          </Card>
        )}

        {activeTab === 'integrations' && (
          <Card className="p-5 space-y-5 bg-white">
            <div className="space-y-3.5">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Logistics & External Data Connectors</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Connect external logistics and order feeds for automated proof verification.
                </p>
              </div>

              <div className="space-y-2">
                {[
                  { name: 'FedEx / Blue Dart Tracking API', status: 'Connected', desc: 'Auto-fetches recipient signature and timestamp proof' },
                  { name: 'Shopify / WooCommerce Order Sync', status: 'Connected', desc: 'Synchronizes order details, customer IP, and billing info' },
                  { name: 'Razorpay Payment Gateway Webhook', status: 'Active (Live)', desc: 'Listens for real-time chargeback events and lifecycle transitions' },
                ].map((item, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-bold text-slate-900">{item.name}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">{item.desc}</div>
                    </div>
                    <span className="px-2.5 py-0.5 text-[10px] font-bold text-emerald-700 bg-emerald-50 rounded-md border border-emerald-200">
                      {item.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <Button type="submit" variant="primary" size="sm" className="font-semibold">
                Save Connectors
              </Button>
            </div>
          </Card>
        )}
      </form>
    </div>
  );
};
