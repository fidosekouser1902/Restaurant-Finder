export function Footer() {
  return (
    <footer className="border-t border-neutral-200 bg-white py-8">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 text-sm text-neutral-500 md:flex-row md:px-6">
        <span className="font-bold text-brand">CraveAI</span>
        <nav className="flex flex-wrap justify-center gap-x-6 gap-y-2">
          <span className="cursor-not-allowed opacity-50">About</span>
          <span className="cursor-not-allowed opacity-50">Contact</span>
          <span className="cursor-not-allowed opacity-50">Terms</span>
          <span className="cursor-not-allowed opacity-50">Privacy</span>
        </nav>
      </div>
    </footer>
  );
}
