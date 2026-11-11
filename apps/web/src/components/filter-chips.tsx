"use client";

export type ReviewFilter = "all" | "pending" | "approved" | "discarded";
const labels: Record<ReviewFilter, string> = { all: "All", pending: "Waiting for review", approved: "Approved", discarded: "Discarded" };

export function FilterChips({ value, counts, onChange, noun }: {
  value: ReviewFilter; counts: Partial<Record<ReviewFilter, number>>; onChange: (next: ReviewFilter) => void; noun: string;
}) {
  return <div className="filter-chips" role="group" aria-label={`Filter ${noun}`}>
    {(Object.keys(labels) as ReviewFilter[]).filter(key => counts[key] !== undefined).map(key =>
      <button key={key} type="button" aria-pressed={value === key} className={value === key ? "active" : ""} onClick={() => onChange(key)}>
        {labels[key]} <strong>{counts[key]}</strong>
      </button>)}
  </div>;
}
