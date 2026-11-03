export function SearchBox({ value, onChange }) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="search" className="text-base font-bold">
        Search by name or address
      </label>
      <input
        id="search"
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="For example: Lady Reading"
        autoComplete="off"
        className="w-full rounded-md border-2 border-ink bg-surface px-3 py-2.5 text-base"
      />
    </div>
  );
}
