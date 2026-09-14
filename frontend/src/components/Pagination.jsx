export function Pagination({ page, totalPages, total, pageSize, onPage }) {
  if (total === 0) return null;

  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  // Compact window of page numbers around the current page.
  const numbers = [];
  const from = Math.max(1, Math.min(page - 1, totalPages - 2));
  const to = Math.min(totalPages, from + 2);
  for (let i = from; i <= to; i += 1) numbers.push(i);

  const navBtn =
    "rounded-md border border-slate-700 bg-slate-950/70 px-2 py-1 text-xs font-medium text-slate-300 transition hover:border-slate-600 hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-35";

  return (
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-2">
      <span className="text-[11px] text-slate-500">
        <span className="font-semibold text-slate-300">
          {first}–{last}
        </span>{" "}
        of {total}
      </span>

      <div className="flex items-center gap-1">
        <button
          type="button"
          className={navBtn}
          onClick={() => onPage(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          ‹
        </button>

        {from > 1 && <span className="px-1 text-[11px] text-slate-600">…</span>}

        {numbers.map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onPage(n)}
            aria-current={n === page ? "page" : undefined}
            className={`rounded-md px-2 py-1 text-xs font-medium transition ${
              n === page
                ? "bg-brand-500/20 text-brand-200 ring-1 ring-brand-500/50"
                : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            }`}
          >
            {n}
          </button>
        ))}

        {to < totalPages && <span className="px-1 text-[11px] text-slate-600">…</span>}

        <button
          type="button"
          className={navBtn}
          onClick={() => onPage(page + 1)}
          disabled={page >= totalPages}
          aria-label="Next page"
        >
          ›
        </button>
      </div>
    </div>
  );
}
