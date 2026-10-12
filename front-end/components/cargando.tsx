export function Cargando() {
  return (
    <main
      aria-busy="true"
      aria-label="Cargando"
      className="mx-auto w-full max-w-6xl flex-1 space-y-4 px-4 pb-12 pt-6"
    >
      <div className="h-9 w-56 animate-pulse rounded-xl bg-muted" />
      <div className="h-5 w-80 max-w-full animate-pulse rounded-lg bg-muted" />
      <div className="h-64 animate-pulse rounded-2xl bg-muted" />
    </main>
  );
}
