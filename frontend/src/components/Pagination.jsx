export function Pagination({ page, totalPages, total, pageSize, onPage }) {
  if (total === 0) return null;

  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  // Compact window of page numbers around the current page.
  const numbers = [];
  const from = Math.max(1, Math.min(page - 1, totalPages - 2));
  const to = Math.min(totalPages, from + 2);
  for (let i = from; i <= to; i += 1) numbers.push(i);

  const button =
    "min-w-[2.75rem] rounded-md border-2 border-ink bg-surface px-3 py-2 text-base font-bold hover:bg-brand-tint disabled:cursor-not-allowed disabled:border-line disabled:text-ink-soft disabled:hover:bg-surface";

  return (
    <nav
      aria-label="Pagination"
      className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-t border-line pt-3"
    >
      <p className="text-base">
        Showing <strong>{first}–{last}</strong> of {total}
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={button}
          onClick={() => onPage(page - 1)}
          disabled={page <= 1}
        >
          Previous
        </button>

        {from > 1 && <span aria-hidden="true">…</span>}

        {numbers.map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onPage(n)}
            aria-label={`Page ${n}`}
            aria-current={n === page ? "page" : undefined}
            className={`${button} ${
              n === page ? "!border-brand !bg-brand !text-white hover:!bg-brand-dark" : ""
            }`}
          >
            {n}
          </button>
        ))}

        {to < totalPages && <span aria-hidden="true">…</span>}

        <button
          type="button"
          className={button}
          onClick={() => onPage(page + 1)}
          disabled={page >= totalPages}
        >
          Next
        </button>
      </div>
    </nav>
  );
}
