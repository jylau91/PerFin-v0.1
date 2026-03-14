"use client";
import { useState, useCallback, useRef } from "react";
import { Upload, FileText, CheckCircle, AlertCircle, X, Loader2 } from "lucide-react";
import { api, type UploadResult } from "@/lib/api";
import Link from "next/link";

interface FileState {
  file: File;
  status: "pending" | "uploading" | "done" | "error";
  result?: UploadResult;
  error?: string;
}

export default function UploadPage() {
  const [files, setFiles] = useState<FileState[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((incoming: File[]) => {
    const pdfs = incoming.filter((f) => f.name.toLowerCase().endsWith(".pdf"));
    setFiles((prev) => [
      ...prev,
      ...pdfs.map((f) => ({ file: f, status: "pending" as const })),
    ]);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      addFiles(Array.from(e.dataTransfer.files));
    },
    [addFiles]
  );

  const removeFile = (idx: number) =>
    setFiles((prev) => prev.filter((_, i) => i !== idx));

  const uploadAll = async () => {
    const pending = files.filter((f) => f.status === "pending");
    for (const item of pending) {
      const idx = files.findIndex((f) => f.file === item.file);
      setFiles((prev) =>
        prev.map((f, i) => (i === idx ? { ...f, status: "uploading" } : f))
      );
      try {
        const result = await api.uploadStatement(item.file);
        setFiles((prev) =>
          prev.map((f, i) => (i === idx ? { ...f, status: "done", result } : f))
        );
      } catch (e: unknown) {
        const error = e instanceof Error ? e.message : "Upload failed";
        setFiles((prev) =>
          prev.map((f, i) => (i === idx ? { ...f, status: "error", error } : f))
        );
      }
    }
  };

  const hasPending = files.some((f) => f.status === "pending");
  const allDone = files.length > 0 && files.every((f) => f.status === "done");

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-2">Upload Statements</h1>
      <p className="text-slate-400 mb-6 text-sm">
        Upload PDF bank statements from DBS, OCBC, UOB, or Maybank. Transactions will be
        parsed and categorised automatically.
      </p>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
          dragging
            ? "border-emerald-400 bg-emerald-900/20"
            : "border-slate-600 hover:border-slate-500 bg-slate-800/50"
        }`}
      >
        <Upload className="mx-auto mb-3 text-slate-400" size={36} />
        <p className="text-slate-300 font-medium">Drop PDF files here</p>
        <p className="text-slate-500 text-sm mt-1">or click to browse</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={(e) => addFiles(Array.from(e.target.files ?? []))}
        />
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          {files.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center gap-3 bg-slate-800 rounded-lg px-4 py-3"
            >
              <FileText size={16} className="text-slate-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white truncate">{item.file.name}</p>
                {item.result && (
                  <p className="text-xs text-emerald-400 mt-0.5">
                    {item.result.transactions_parsed} transactions parsed ·{" "}
                    {item.result.transactions_categorised} categorised ·{" "}
                    {item.result.statement.bank}
                  </p>
                )}
                {item.error && (
                  <p className="text-xs text-red-400 mt-0.5">{item.error}</p>
                )}
              </div>
              {item.status === "uploading" && (
                <Loader2 size={16} className="text-emerald-400 animate-spin shrink-0" />
              )}
              {item.status === "done" && (
                <CheckCircle size={16} className="text-emerald-400 shrink-0" />
              )}
              {item.status === "error" && (
                <AlertCircle size={16} className="text-red-400 shrink-0" />
              )}
              {item.status === "pending" && (
                <button
                  onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                  className="text-slate-500 hover:text-slate-300"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 mt-5">
        {hasPending && (
          <button
            onClick={uploadAll}
            className="bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Upload {files.filter((f) => f.status === "pending").length} file
            {files.filter((f) => f.status === "pending").length > 1 ? "s" : ""}
          </button>
        )}
        {allDone && (
          <Link
            href="/"
            className="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            View Dashboard
          </Link>
        )}
      </div>
    </div>
  );
}
