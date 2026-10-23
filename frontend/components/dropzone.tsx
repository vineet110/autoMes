"use client";

import { useRef, useState, type ReactNode } from "react";
import { cn } from "./ui";

export function Dropzone({
  onFiles,
  accept,
  icon,
  title,
  hint,
  compact,
  disabled,
}: {
  onFiles: (files: File[]) => void;
  accept?: string;
  icon: ReactNode;
  title: ReactNode;
  hint?: ReactNode;
  compact?: boolean;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handle = (list: FileList | null) => {
    if (list?.length) onFiles(Array.from(list));
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-disabled={disabled}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && !disabled && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) handle(e.dataTransfer.files);
      }}
      className={cn(
        "flex cursor-pointer items-center gap-4 rounded-xl border-2 border-dashed transition",
        "focus-visible:outline-2 focus-visible:outline-brand-500",
        compact ? "px-4 py-3" : "flex-col justify-center px-6 py-8 text-center",
        dragging ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-slate-50/50 hover:border-slate-300 hover:bg-slate-50",
        disabled && "cursor-not-allowed opacity-60",
      )}
    >
      <div className={cn("rounded-full bg-white p-2.5 text-slate-500 shadow-sm ring-1 ring-slate-200", dragging && "text-brand-600")}>
        {icon}
      </div>
      <div className={compact ? "text-left" : ""}>
        <p className="text-sm font-medium text-slate-700">{title}</p>
        {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={accept}
        className="hidden"
        onChange={(e) => {
          handle(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
