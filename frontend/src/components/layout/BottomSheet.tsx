"use client";

import { useEffect, useRef } from "react";
import { X } from "lucide-react";

interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}

export function BottomSheet({ isOpen, onClose, title, children }: BottomSheetProps) {
  const sheetRef = useRef<HTMLDivElement>(null);
  const startY = useRef(0);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const handleTouchStart = (e: React.TouchEvent) => {
    startY.current = e.touches[0].clientY;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const delta = e.changedTouches[0].clientY - startY.current;
    if (delta > 80) onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 animate-fade-in"
        style={{ background: "rgba(0, 0, 0, 0.5)" }}
        onClick={onClose}
      />

      {/* Sheet */}
      <div
        ref={sheetRef}
        className="absolute bottom-0 left-0 right-0 flex flex-col overflow-hidden"
        style={{
          background: "var(--bg-primary)",
          borderTopLeftRadius: "var(--radius-card)",
          borderTopRightRadius: "var(--radius-card)",
          maxHeight: "70vh",
          animation: "slideUp 0.3s ease-out forwards",
        }}
      >
        {/* Drag handle */}
        <div
          className="flex flex-col items-center pt-3 pb-2 cursor-grab"
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          <div
            className="h-1 w-10 rounded-full"
            style={{ background: "var(--border-medium)" }}
          />
        </div>

        {/* Header */}
        {title && (
          <div
            className="flex items-center justify-between px-4 pb-3 border-b"
            style={{ borderColor: "var(--border-light)" }}
          >
            <h3
              className="text-sm font-semibold uppercase"
              style={{ color: "var(--text-primary)" }}
            >
              {title}
            </h3>
            <button
              onClick={onClose}
              className="rounded p-1 transition-all duration-200 hover:scale-[1.1]"
              style={{ color: "var(--text-secondary)" }}
            >
              <X size={18} />
            </button>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {children}
        </div>
      </div>
    </div>
  );
}
