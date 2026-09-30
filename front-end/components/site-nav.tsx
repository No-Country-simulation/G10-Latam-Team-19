import Link from "next/link";

const ENLACES = [
  { href: "/", etiqueta: "Inicio" },
  { href: "/historial", etiqueta: "Historial" },
  { href: "/auditoria", etiqueta: "Auditoría" },
  { href: "/faq", etiqueta: "FAQ" },
];

export function SiteNav() {
  return (
    <header className="border-b">
      <nav className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="font-semibold">
          MediFlow
        </Link>
        <ul className="flex gap-4 text-sm text-muted-foreground">
          {ENLACES.map(({ href, etiqueta }) => (
            <li key={href}>
              <Link href={href} className="hover:text-foreground">
                {etiqueta}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
