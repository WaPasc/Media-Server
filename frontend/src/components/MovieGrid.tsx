// frontend/src/components/MovieGrid.tsx
import type { Movie } from "../api";

interface MovieGridProps {
  movies: Movie[];
  onPlayMovie: (movie: Movie) => void;
}

export default function MovieGrid({ movies, onPlayMovie }: MovieGridProps) {
  return (
    <div className="min-h-screen bg-neutral-950 text-white p-6 md:p-12">
      <h1 className="text-4xl font-extrabold mb-10 text-white tracking-wide">
        My Media Server
      </h1>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
        {movies.map((movie) => (
          <div
            key={movie.id}
            onClick={() => onPlayMovie(movie)}
            className="group relative cursor-pointer transition-all duration-300 hover:scale-105 hover:z-10"
          >
            {/* Poster Aspect Ratio Container */}
            <div className="aspect-2/3 w-full bg-neutral-800 rounded-lg shadow-lg overflow-hidden border border-neutral-800 group-hover:border-neutral-600 group-hover:shadow-red-900/20">
              {movie.poster_url ? (
                <img
                  src={movie.poster_url}
                  alt={movie.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-neutral-500 text-sm p-4 text-center">
                  No Poster Available
                </div>
              )}
            </div>

            {/* Text Metadata */}
            <div className="mt-3">
              <h3 className="text-sm md:text-base font-semibold text-neutral-100 truncate">
                {movie.title}
              </h3>
              <p className="text-xs text-neutral-400 font-medium">
                {movie.year || "Unknown Year"}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
