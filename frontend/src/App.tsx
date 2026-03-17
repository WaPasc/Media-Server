import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchMovies, type Movie } from "./api";
import MovieGrid from "./components/MovieGrid";
import VideoPlayer from "./components/VideoPlayer";

function App() {
  const [playingMovie, setPlayingMovie] = useState<Movie | null>(null);

  const {
    data: movies = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["movies"],
    queryFn: fetchMovies,
    retry: 2,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#09090B] flex flex-col items-center justify-center text-white">
        <div className="w-12 h-12 border-4 border-neutral-800 border-t-indigo-500 rounded-full animate-spin mb-4"></div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-[#09090B] flex flex-col items-center justify-center text-white p-6 text-center">
        <div className="bg-rose-950/20 border border-rose-900/50 p-8 rounded-2xl max-w-lg">
          <h2 className="text-2xl font-bold text-rose-500 mb-4">
            Connection Failed
          </h2>
          <p className="text-neutral-300 mb-6">
            {error instanceof Error ? error.message : "Network error"}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-rose-600 hover:bg-rose-700 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#09090B] min-h-screen font-sans selection:bg-indigo-500 selection:text-white">
      {playingMovie ? (
        <VideoPlayer
          movie={playingMovie}
          onBack={() => setPlayingMovie(null)}
        />
      ) : (
        <MovieGrid movies={movies} onPlayMovie={setPlayingMovie} />
      )}
    </div>
  );
}

export default App;
