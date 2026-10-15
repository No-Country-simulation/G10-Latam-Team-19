import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { SiteNav } from "@/components/site-nav";
import { MODO_DEMO } from "@/lib/api";

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MediFlow",
  description:
    "Triaje y enrutamiento inteligente de documentos clínicos.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {MODO_DEMO && (
          <p className="bg-secondary px-4 py-1.5 text-center text-xs text-secondary-foreground">
            Modo demo: se muestran datos de ejemplo, no pacientes reales.
          </p>
        )}
        <SiteNav />
        {children}
      </body>
    </html>
  );
}
