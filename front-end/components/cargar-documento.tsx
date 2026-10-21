"use client";

import { startTransition, useActionState, useRef, useState } from "react";
import { ArrowRight, ChevronDown, FileText, Loader2, Upload, X } from "lucide-react";
import { cargarDocumento, type EstadoCarga } from "@/app/actions";
import {
  clasificarArchivo,
  EXTENSIONES_ACEPTADAS,
  formatearTamano,
} from "@/lib/archivos";
import { cn } from "@/lib/utils";
import { CANALES, MAX_TEXTO, MIN_TEXTO } from "@/lib/validacion";
import type { TipoArchivo } from "@/types/triage";

type Pestana = "archivo" | "texto";

interface ArchivoElegido {
  nombre: string;
  bytes: number;
  /** Texto listo para enviar; null si el archivo no se puede procesar. */
  texto: string | null;
  tipo: TipoArchivo;
  aviso: string | null;
  /** El texto lo leyó una IA desde una imagen: la persona debe revisarlo antes de enviarlo. */
  transcripto?: boolean;
  /** Mensaje informativo que no impide enviar (p. ej. se leyeron solo las primeras páginas). */
  nota?: string | null;
}

type ResultadoOcr = { ok: true; texto: string; nota: string | null } | { ok: false; error: string };

/** Pide al backend (vía /api/ocr) que lea una imagen o un PDF escaneado. */
async function transcribir(file: File): Promise<ResultadoOcr> {
  const form = new FormData();
  form.append("archivo", file);
  try {
    const res = await fetch("/api/ocr", { method: "POST", body: form, signal: AbortSignal.timeout(200_000) });
    const cuerpo: unknown = await res.json().catch(() => null);
    const datos = cuerpo as { texto?: unknown; paginas?: unknown; paginasTotales?: unknown; error?: unknown } | null;
    if (!res.ok || typeof datos?.texto !== "string") {
      return { ok: false, error: typeof datos?.error === "string" ? datos.error : "No se pudo leer el archivo." };
    }
    const leidas = Number(datos.paginas);
    const totales = Number(datos.paginasTotales);
    const nota = totales > leidas ? `Se leyeron las primeras ${leidas} de ${totales} páginas.` : null;
    return { ok: true, texto: datos.texto, nota };
  } catch {
    return { ok: false, error: "No se pudo leer el archivo. Revisá la conexión y probá de nuevo." };
  }
}

/** Extrae el texto de un PDF en el navegador. unpdf se carga solo cuando hace falta. */
async function extraerTextoPdf(file: File): Promise<string> {
  const { extractText, getDocumentProxy } = await import("unpdf");
  const pdf = await getDocumentProxy(new Uint8Array(await file.arrayBuffer()));
  const { text } = await extractText(pdf, { mergePages: true });
  return text.trim();
}

const inicial: EstadoCarga = { error: null };

export function CargarDocumento() {
  const [estado, accion, pendiente] = useActionState(cargarDocumento, inicial);
  const [pestana, setPestana] = useState<Pestana>("archivo");
  const [texto, setTexto] = useState("");
  const [archivo, setArchivo] = useState<ArchivoElegido | null>(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [leyendo, setLeyendo] = useState(false);
  const [transcribiendo, setTranscribiendo] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  // Cada archivo elegido toma un turno: si se elige otro mientras uno se lee, el resultado viejo se descarta.
  const turnoActual = useRef(0);

  async function elegir(file: File | undefined) {
    if (!file) return;
    const turno = ++turnoActual.current;
    const vigente = () => turno === turnoActual.current;
    const base = { nombre: file.name, bytes: file.size };
    const clase = clasificarArchivo(file);

    if (clase.clase === "rechazado") {
      setLeyendo(false);
      setTranscribiendo(false);
      setArchivo({ ...base, texto: null, tipo: "TEXTO", aviso: clase.motivo });
      return;
    }

    setLeyendo(true);
    setTranscribiendo(false);
    setArchivo(null);

    /** Lee la imagen o el PDF escaneado con IA y deja el texto para que la persona lo revise. */
    async function conIa(tipo: TipoArchivo) {
      setTranscribiendo(true);
      const r = await transcribir(file as File);
      if (!vigente()) return;
      setArchivo(
        r.ok
          ? { ...base, texto: r.texto, tipo, aviso: null, transcripto: true, nota: r.nota }
          : { ...base, texto: null, tipo, aviso: r.error },
      );
    }

    try {
      if (clase.clase === "imagen") {
        await conIa("IMAGEN");
        return;
      }

      const texto = clase.clase === "pdf" ? await extraerTextoPdf(file) : (await file.text()).trim();
      if (!vigente()) return;
      const tipo = clase.clase === "pdf" ? "PDF" : clase.tipo;

      // Un PDF sin texto seleccionable es un escaneo: se lee como imagen.
      if (clase.clase === "pdf" && texto.length < MIN_TEXTO) {
        await conIa("PDF");
        return;
      }

      let aviso: string | null = null;
      if (texto.length < MIN_TEXTO) {
        aviso = "El archivo casi no tiene texto.";
      } else if (texto.length > MAX_TEXTO) {
        aviso = "El documento es demasiado largo para procesarlo.";
      }
      setArchivo({ ...base, texto: aviso ? null : texto, tipo, aviso });
    } catch {
      if (vigente()) setArchivo({ ...base, texto: null, tipo: "TEXTO", aviso: "No se pudo leer el archivo." });
    } finally {
      if (vigente()) {
        setLeyendo(false);
        setTranscribiendo(false);
      }
    }
  }

  const listo =
    pestana === "texto"
      ? texto.trim().length >= MIN_TEXTO
      : Boolean(archivo?.texto && archivo.texto.trim().length >= MIN_TEXTO && !archivo.aviso && !leyendo);

  return (
    <form
      // onSubmit en lugar de action={accion}: con `action`, React resetea el formulario al
      // terminar y, tras un error, el canal volvía al valor por defecto sin que se notara.
      onSubmit={(e) => {
        e.preventDefault();
        const datos = new FormData(e.currentTarget);
        startTransition(() => accion(datos));
      }}
      className="space-y-5 rounded-3xl bg-card p-5 shadow-lg ring-1 ring-foreground/5"
    >
      <div role="tablist" className="inline-flex gap-1 rounded-xl bg-muted/70 p-1 text-sm">
        {(
          [
            ["archivo", "Subir archivo"],
            ["texto", "Pegar texto"],
          ] as const
        ).map(([id, etiqueta]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={pestana === id}
            onClick={() => setPestana(id)}
            className={cn(
              "rounded-lg px-4 py-1.5 transition-colors",
              pestana === id
                ? "bg-card font-semibold shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {etiqueta}
          </button>
        ))}
      </div>

      {pestana === "archivo" ? (
        <div className="space-y-3">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setArrastrando(true);
            }}
            onDragLeave={() => setArrastrando(false)}
            onDrop={(e) => {
              e.preventDefault();
              setArrastrando(false);
              void elegir(e.dataTransfer.files[0]);
            }}
            className={cn(
              "flex min-h-48 flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-4 py-8 text-center transition-colors",
              arrastrando ? "border-primary bg-secondary" : "border-primary/30 bg-secondary/40",
            )}
          >
            <span className="grid size-12 place-items-center rounded-2xl bg-secondary text-primary">
              <Upload className="size-5" />
            </span>
            <p className="text-sm font-medium">
              Arrastrá tu PDF o imagen acá, o{" "}
              <button
                type="button"
                onClick={() => input.current?.click()}
                className="text-primary underline-offset-4 hover:underline"
              >
                seleccioná un archivo
              </button>
            </p>
            <p className="text-xs text-muted-foreground">PDF, JPG, PNG, TXT o JSON · hasta 10 MB</p>
            <input
              ref={input}
              type="file"
              accept={EXTENSIONES_ACEPTADAS.join(",")}
              className="sr-only"
              aria-label="Seleccionar archivo"
              onChange={(e) => void elegir(e.target.files?.[0])}
            />
          </div>

          {leyendo && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              {transcribiendo ? "Leyendo el documento con IA… puede tardar unos segundos" : "Leyendo el archivo…"}
            </p>
          )}

          {archivo && !leyendo && (
            <div
              className={cn(
                "flex items-start gap-3 rounded-xl border p-3 text-sm",
                archivo.aviso && "border-destructive/40 bg-destructive/5",
              )}
            >
              <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{archivo.nombre}</p>
                <p className="text-xs text-muted-foreground">{formatearTamano(archivo.bytes)}</p>
                {archivo.aviso && <p className="mt-1 text-xs text-destructive">{archivo.aviso}</p>}
                {archivo.nota && <p className="mt-1 text-xs text-muted-foreground">{archivo.nota}</p>}
              </div>
              <button
                type="button"
                aria-label="Quitar archivo"
                onClick={() => {
                  turnoActual.current++;
                  setArchivo(null);
                  if (input.current) input.current.value = "";
                }}
                className="rounded-md p-1 text-muted-foreground hover:bg-muted"
              >
                <X className="size-4" />
              </button>
            </div>
          )}

          {archivo && !archivo.aviso && archivo.transcripto && (
            <div className="space-y-2">
              <label htmlFor="texto_transcripto" className="block text-sm font-medium">
                Texto leído por la IA
              </label>
              <p className="text-xs text-muted-foreground">
                Revisalo y corregí lo que haga falta antes de procesar. Lo marcado como [ilegible] no se pudo leer con
                certeza.
              </p>
              <textarea
                id="texto_transcripto"
                name="documento_texto"
                value={archivo.texto ?? ""}
                onChange={(e) => setArchivo((a) => (a ? { ...a, texto: e.target.value } : a))}
                rows={8}
                maxLength={MAX_TEXTO}
                className="min-h-40 w-full resize-y rounded-2xl border bg-card p-4 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <input type="hidden" name="tipo_archivo" value={archivo.tipo} />
            </div>
          )}

          {archivo?.texto && !archivo.aviso && !archivo.transcripto && (
            <>
              <input type="hidden" name="documento_texto" value={archivo.texto} />
              <input type="hidden" name="tipo_archivo" value={archivo.tipo} />
            </>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <label htmlFor="documento_texto" className="sr-only">
            Texto del documento
          </label>
          <textarea
            id="documento_texto"
            name="documento_texto"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            rows={7}
            maxLength={MAX_TEXTO}
            placeholder="Pegá acá el texto de la receta, informe, orden o epicrisis…"
            className="min-h-48 w-full resize-y rounded-2xl border-2 border-dashed border-primary/30 bg-secondary/40 p-4 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <input type="hidden" name="tipo_archivo" value="TEXTO" />
        </div>
      )}

      <div className="flex flex-wrap items-stretch gap-3">
        <div className="relative min-w-52 flex-1 rounded-xl border bg-card px-4 py-2 focus-within:ring-2 focus-within:ring-ring">
          <label htmlFor="canal_origen" className="block text-xs text-muted-foreground">
            Canal de origen
          </label>
          <select
            id="canal_origen"
            name="canal_origen"
            className="w-full appearance-none bg-transparent pr-6 text-sm font-medium outline-none"
          >
            {Object.entries(CANALES).map(([valor, etiqueta]) => (
              <option key={valor} value={valor}>
                {etiqueta}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute top-1/2 right-4 size-4 -translate-y-1/2 text-muted-foreground" />
        </div>
        <button
          type="submit"
          disabled={pendiente || !listo}
          className="inline-flex h-14 items-center gap-2 rounded-full bg-foreground px-7 text-sm font-semibold text-background transition-opacity disabled:opacity-50"
        >
          {pendiente && <Loader2 className="size-4 animate-spin" />}
          Procesar documento
          {!pendiente && <ArrowRight className="size-4" />}
        </button>
      </div>

      {estado.error && (
        <p role="alert" className="text-sm text-destructive">
          {estado.error}
        </p>
      )}
    </form>
  );
}
