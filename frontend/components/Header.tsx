import Link from "next/link";

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-neutral-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 md:px-6">
        <Link href="/" className="text-xl font-bold tracking-tight text-brand">
          CraveAI
        </Link>
        <nav className="hidden items-center gap-8 text-sm font-medium text-neutral-600 md:flex">
          <span className="text-brand">Discover</span>
          <span className="cursor-not-allowed opacity-40">Collections</span>
          <span className="cursor-not-allowed opacity-40">Add Restaurant</span>
        </nav>
        <div className="flex items-center gap-3 text-neutral-400">
          <span className="hidden text-xs text-neutral-400 sm:inline">Demo UI</span>
        </div>
      </div>
    </header>
  );
}
