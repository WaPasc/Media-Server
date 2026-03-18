// frontend/src/components/MovieDetails.tsx
import { type Movie } from "../api";

interface MovieDetailsProps {
  movie: Movie;
  onBack: () => void;
  onPlay: (fileId: number, title: string) => void;
}

export function MovieDetails({ movie, onBack, onPlay }: MovieDetailsProps) {
  return (
    <div className="min-h-screen bg-[#09090B] text-white relative overflow-hidden animate-in fade-in duration-500">
      <div className="absolute top-0 left-0 w-full h-[75vh] z-0 select-none pointer-events-none">
        {movie.backdrop_url ? (
          <img
            src={movie.backdrop_url}
            alt={movie.title}
            className="w-full h-full object-cover opacity-60"
          />
        ) : (
          <div className="w-full h-full bg-neutral-900" />
        )}
        <div className="absolute inset-0 bg-linear-to-t from-[#09090B] via-[#09090B]/60 to-transparent" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 sm:px-12 pt-[40vh] pb-20">
        <button
          onClick={onBack}
          className="group mb-8 flex items-center gap-2 text-neutral-300 hover:text-white transition-colors"
        >
          <span className="text-2xl group-hover:-translate-x-1 transition-transform">
            ←
          </span>
          <span className="font-medium">Back to Library</span>
        </button>

        <h1 className="text-5xl md:text-7xl font-extrabold mb-4 drop-shadow-2xl tracking-tight text-white">
          {movie.title}
        </h1>
        <p className="text-xl md:text-2xl text-neutral-300 mb-10 font-medium drop-shadow-md">
          {movie.year || "Unknown Year"}
        </p>

        <button
          onClick={() => {
            if (movie.file_id) onPlay(movie.file_id, movie.title);
            else alert("No physical file is attached to this movie!");
          }}
          className="flex items-center gap-3 bg-white text-black px-8 py-3 rounded-lg font-bold text-xl hover:bg-neutral-200 transition-all hover:scale-105 shadow-[0_0_40px_rgba(255,255,255,0.3)] mb-12"
        >
          <svg className="w-7 h-7" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
          Play Movie
        </button>

        <div className="max-w-3xl bg-black/40 p-6 rounded-2xl backdrop-blur-sm border border-white/5">
          <h3 className="text-xl font-semibold mb-3 text-neutral-100">
            Overview
          </h3>
          <p className="text-lg text-neutral-300 leading-relaxed">
            {movie.overview || "No overview available for this title."}
          </p>
        </div>
      </div>
    </div>
  );
}
