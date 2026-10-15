"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus, Search } from "lucide-react";
import { cn } from "@/lib/utils";

const ENLACES = [
  { href: "/", etiqueta: "Cargar" },
  { href: "/dashboard", etiqueta: "Dashboard" },
  { href: "/historial", etiqueta: "Historial" },
  { href: "/auditoria", etiqueta: "Auditoría" },
  { href: "/faq", etiqueta: "FAQ" },
];

export function SiteNav() {
  const pathname = usePathname();
  const buscador = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const atajo = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        buscador.current?.focus();
      }
    };
    window.addEventListener("keydown", atajo);
    return () => window.removeEventListener("keydown", atajo);
  }, []);

  return (
    <header>
      <nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold">
          <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
            <Plus className="size-4" strokeWidth={3} />
          </span>
          MediFlow
        </Link>
        <ul className="flex max-w-full gap-1 overflow-x-auto rounded-full bg-card p-1 text-sm shadow-sm ring-1 ring-foreground/5 [scrollbar-width:none]">
          {ENLACES.map(({ href, etiqueta }) => {
            const activo = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={activo ? "page" : undefined}
                  className={cn(
                    "block rounded-full px-3 py-1.5 whitespace-nowrap transition-colors sm:px-4",
                    activo
                      ? "bg-secondary font-semibold text-secondary-foreground"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {etiqueta}
                </Link>
              </li>
            );
          })}
        </ul>
        <div className="flex items-center gap-2">
          <form
            action="/historial"
            role="search"
            className="flex items-center gap-2 rounded-full bg-card px-3 py-1.5 shadow-sm ring-1 ring-foreground/5"
          >
            <Search className="size-4 text-muted-foreground" />
            <input
              ref={buscador}
              name="q"
              type="search"
              placeholder="Buscar documento"
              aria-label="Buscar documento"
              className="w-36 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <kbd className="hidden rounded-md bg-muted px-1.5 py-0.5 text-xs text-muted-foreground sm:block">
              ⌘K
            </kbd>
          </form>
          {/* Sesión de usuario fuera del alcance del proyecto.
          <span
            aria-label="Operador"
            className="grid size-9 place-items-center rounded-full bg-secondary text-xs font-semibold text-secondary-foreground"
          >
            OA
          </span>
          */}
        </div>
      </nav>
    </header>
  );
}
