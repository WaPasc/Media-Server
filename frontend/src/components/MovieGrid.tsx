import { type Movie } from "../api";
import logo from "../assets/logo-green-cyan.svg";

interface MovieGridProps {
  movies: Movie[];
  onPlayMovie: (movie: Movie) => void;
}

export default function MovieGrid({ movies, onPlayMovie }: MovieGridProps) {
  return (
    <div className="min-h-screen bg-[#09090B] text-white p-6 md:p-12">
      <div className="flex items-center gap-4 mb-10">
        <img src={logo} alt="Logo" className="w-12 h-12" />
        <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-linear-to-r from-indigo-500 via-purple-500 to-pink-500 tracking-wide">
          My Media Server
        </h1>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
        {movies.map((movie) => (
          <div
            key={movie.id}
            onClick={() => onPlayMovie(movie)}
            className="group relative cursor-pointer transition-all duration-300 hover:scale-105 hover:z-10"
          >
            <div className="aspect-2/3 w-full bg-neutral-900 rounded-xl shadow-lg overflow-hidden border border-neutral-800 group-hover:border-neutral-600 group-hover:shadow-purple-500/20 transition-all">
              {movie.poster_url ? (
                <img
                  src={movie.poster_url}
                  alt={movie.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-neutral-600 text-sm p-4">
                  No Poster
                </div>
              )}
            </div>
            <div className="mt-3 px-1">
              <h3 className="text-sm md:text-base font-semibold text-neutral-100 truncate">
                {movie.title}
              </h3>
              <p className="text-xs text-neutral-500 font-medium">
                {movie.year}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
