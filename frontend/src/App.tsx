// frontend/src/App.tsx
import { useState, useEffect } from "react";
import { fetchMovies, type Movie } from "./api";
import MovieGrid from "./components/MovieGrid";
import VideoPlayer from "./components/VideoPlayer";

function App() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [playingMovie, setPlayingMovie] = useState<Movie | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const loadMovies = async () => {
      const data = await fetchMovies();
      setMovies(data);
      setLoading(false);
    };
    loadMovies();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center text-white">
        <div className="w-12 h-12 border-4 border-neutral-800 border-t-red-600 rounded-full animate-spin mb-4"></div>
        <p className="text-neutral-400 font-medium animate-pulse">
          Loading library...
        </p>
      </div>
    );
  }

  return (
    <div className="bg-neutral-950 min-h-screen font-sans selection:bg-red-600 selection:text-white">
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
