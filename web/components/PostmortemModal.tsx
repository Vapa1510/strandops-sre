"use client";

import React, { useState } from "react";
import { X, Copy, Download, Check, FileText } from "lucide-react";

import { APP_CONFIG } from "@/lib/config";

interface PostmortemModalProps {
  isOpen: boolean;
  onClose: () => void;
  markdown: string;
}

export function PostmortemModal({ isOpen, onClose, markdown }: PostmortemModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `incident-postmortem-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#02060f]/80 backdrop-blur-md">
      <div className="relative w-full max-w-4xl max-h-[85vh] flex flex-col rounded-2xl border border-brand/25 bg-[#071225]/95 shadow-neon-blue overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-brand/15 bg-brand/5">
          <div className="flex items-center gap-2.5">
            <FileText className="w-5 h-5 text-brand-bright" />
            <h3 className="font-display text-base font-bold text-white">Incident postmortem</h3>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={handleCopy} className="btn-ghost !py-1.5 !px-3 !text-xs">
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              <span>{copied ? "Copied" : "Copy Markdown"}</span>
            </button>

            <button onClick={handleDownload} className="btn-brand !py-1.5 !px-3 !text-xs">
              <Download className="w-3.5 h-3.5" />
              <span>Download .md</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-white/5 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <pre className="whitespace-pre-wrap font-mono text-xs text-slate-200 bg-[#050a14]/80 p-5 rounded-xl border border-brand/15 leading-relaxed">
            {markdown}
          </pre>
        </div>

        <div className="px-6 py-3 border-t border-brand/15 bg-brand/5 flex items-center justify-between text-[11px] text-slate-400">
          <span className="font-mono">
            AWS Account: {APP_CONFIG.awsAccountId} · Region: {APP_CONFIG.awsRegion}
          </span>
          <button onClick={onClose} className="btn-ghost !py-1.5 !px-4 !text-xs">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
