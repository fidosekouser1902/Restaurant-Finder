import Image from "next/image";

export function Hero() {
  return (
    <section className="relative h-52 overflow-hidden md:h-60">
      <Image
        src="/design-reference.png"
        alt=""
        fill
        className="object-cover object-center blur-[2px] brightness-[0.55]"
        priority
        sizes="100vw"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/35 to-transparent" />
      <div className="relative z-10 mx-auto flex h-full max-w-7xl flex-col justify-end px-4 pb-8 md:px-6">
        <h1 className="text-3xl font-bold tracking-tight text-white drop-shadow md:text-4xl">
          AI Restaurant Finder
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-white/90 md:text-base">
          Personalized restaurant recommendations powered by AI. Expertly curated for your palate.
        </p>
      </div>
    </section>
  );
}
