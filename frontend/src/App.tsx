// frontend/src/App.tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  fetchContinueWatching,
  fetchMovies,
  fetchShows,
  type Media,
  type Movie,
} from "./api";
import { VideoPlayer } from "./components/VideoPlayer";
import { MovieDetails } from "./components/MovieDetails";
import { ShowDetails } from "./components/ShowDetails";
import { MediaGrid } from "./components/MediaGrid";

export default function App() {
  const [activeTab, setActiveTab] = useState<"movies" | "shows">("movies");
  
  // The currently clicked poster (Movie or Show)
  const [selectedMedia, setSelectedMedia] = useState<Media | null>(null);
  
  // The specific file to stream and its display title
  const [playingMedia, setPlayingMedia] = useState<{
    fileId: number;
    title: string;
    startAt?: number;
  } | null>(null);

  const { data: movies = [], isLoading: loadingMovies, isError: isMovieError } = useQuery({
    queryKey: ["movies"],
    queryFn: fetchMovies,
    retry: 2,
  });

  const { data: shows = [], isLoading: loadingShows, isError: isShowError } = useQuery({
    queryKey: ["shows"],
    queryFn: fetchShows,
    retry: 2,
  });

  const { data: continueWatching = [] } = useQuery({
    queryKey: ["continueWatching"],
    queryFn: fetchContinueWatching,
    retry: 2,
  });

  const isLoading = loadingMovies || loadingShows;
  const isError = isMovieError || isShowError;

  // --- ROUTING LOGIC ---

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
          <h2 className="text-2xl font-bold text-rose-500 mb-4">Connection Failed</h2>
          <p className="text-neutral-300 mb-6">Could not connect to the media server.</p>
          <button onClick={() => window.location.reload()} className="px-6 py-2 bg-rose-600 hover:bg-rose-700 rounded-lg transition-colors">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // 1. Watching a Video (Movie or Episode)
  if (playingMedia) {
    return (
      <VideoPlayer
        fileId={playingMedia.fileId}
        title={playingMedia.title}
        startAt={playingMedia.startAt}
        onBack={() => setPlayingMedia(null)}
      />
    );
  }

  // 2. Looking at Details
  if (selectedMedia) {
    // Type Guard: Does it have a file_id property? If so, it's a Movie!
    if ("file_id" in selectedMedia) {
      return (
        <MovieDetails
          movie={selectedMedia as Movie}
          onBack={() => setSelectedMedia(null)}
          onPlay={(fileId, title) => setPlayingMedia({ fileId, title, startAt: 0 })}
        />
      );
    }
    
    // Otherwise, it's a TV Show!
    return (
      <ShowDetails
        show={selectedMedia}
        onBack={() => setSelectedMedia(null)}
        onPlay={(fileId, title) => setPlayingMedia({ fileId, title, startAt: 0 })}
      />
    );
  }

  // 3. Browsing the Grid (Main Menu)
  return (
    <div className="bg-[#09090B] min-h-screen font-sans selection:bg-indigo-500 selection:text-white flex flex-col">
      {/* Header / Brand */}
      <div className="flex items-center justify-center md:justify-start gap-4 p-6 md:px-12 pt-10">
        <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-linear-to-r from-indigo-500 via-purple-500 to-pink-500 tracking-wide">
          My Media Server
        </h1>
      </div>

      {/* Navigation Tabs */}
      <div className="flex justify-center gap-8 py-2 border-b border-neutral-800/80 mb-6">
        <button
          onClick={() => setActiveTab("movies")}
          className={`text-lg font-bold transition-all px-2 py-4 relative ${
            activeTab === "movies" ? "text-white" : "text-neutral-500 hover:text-neutral-300"
          }`}
        >
          Movies
          {activeTab === "movies" && (
            <div className="absolute bottom-0 left-0 w-full h-1 bg-linear-to-r from-indigo-500 to-purple-500 rounded-t-full" />
          )}
        </button>
        <button
          onClick={() => setActiveTab("shows")}
          className={`text-lg font-bold transition-all px-2 py-4 relative ${
            activeTab === "shows" ? "text-white" : "text-neutral-500 hover:text-neutral-300"
          }`}
        >
          TV Shows
          {activeTab === "shows" && (
            <div className="absolute bottom-0 left-0 w-full h-1 bg-linear-to-r from-purple-500 to-pink-500 rounded-t-full" />
          )}
        </button>
      </div>

      {/* Grid Content */}
      <MediaGrid
        items={activeTab === "movies" ? movies : shows}
        onItemClick={setSelectedMedia}
        activeTab={activeTab}
        continueWatchingItems={continueWatching}
        onResume={(fileId, title, startAt) =>
          setPlayingMedia({ fileId, title, startAt })
        }
      />
    </div>
  );
}