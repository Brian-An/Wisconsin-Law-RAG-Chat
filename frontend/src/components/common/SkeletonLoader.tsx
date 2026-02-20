"use client";

export function SkeletonLoader() {
  return (
    <div className="flex flex-col gap-3 p-4 animate-fade-in">
      <div className="skeleton h-4 w-3/4 rounded" />
      <div className="skeleton h-4 w-full rounded" />
      <div className="skeleton h-4 w-5/6 rounded" />
      <div className="skeleton h-4 w-2/3 rounded" />
    </div>
  );
}
