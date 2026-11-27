export default function App() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-3xl flex-col justify-center px-6 py-16 sm:px-10">
      <p className="mb-4 text-sm font-semibold tracking-widest text-cyan-300 uppercase">
        Project foundation
      </p>
      <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">BlueGrid 2.0</h1>
      <p className="mt-6 text-lg leading-relaxed text-slate-300">
        Renewable energy planning for island, coastal, and regional energy systems.
      </p>
      <div className="mt-10 border-t border-slate-700 pt-8">
        <h2 className="text-lg font-semibold">Frontend structure is ready</h2>
        <p className="mt-3 leading-relaxed text-slate-300">
          This starter confirms that React, TypeScript, Vite, and Tailwind CSS are
          configured. The core planning screens are scheduled for the next
          development phase. The scientific backend is available as a separate
          Flask API.
        </p>
        <p className="mt-5 text-sm leading-relaxed text-slate-400">
          See the project README for the architecture, folder responsibilities,
          and development status.
        </p>
      </div>
    </main>
  )
}
