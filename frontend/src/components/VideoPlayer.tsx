// frontend/src/components/VideoPlayer.tsx
import { type Movie, getStreamUrl } from "../api";

interface VideoPlayerProps {
  movie: Movie;
  onBack: () => void;
}

export default function VideoPlayer({ movie, onBack }: VideoPlayerProps) {
  // Safety check: if no file is attached, don't try to load the video player
  if (!movie.file_id) {
    return (
      <div className="min-h-screen bg-neutral-950 text-white flex flex-col items-center justify-center p-6 text-center">
        <h2 className="text-3xl font-bold mb-4">File Missing</h2>
        <p className="text-neutral-400 mb-8 max-w-md">
          Oops! There is no physical media file attached to "{movie.title}" in
          the database.
        </p>
        <button
          onClick={onBack}
          className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition-colors"
        >
          Back to Library
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black flex flex-col">
      {/* Header / Nav */}
      <div className="p-6 flex items-center gap-6 absolute top-0 left-0 w-full z-10 bg-gradient-to-b from-black/80 to-transparent">
        <button
          onClick={onBack}
          className="group flex items-center gap-2 px-4 py-2 text-neutral-300 hover:text-white transition-colors"
        >
          <span className="text-2xl group-hover:-translate-x-1 transition-transform">
            ←
          </span>
          <span className="font-medium text-lg">Back</span>
        </button>
        <h2 className="text-2xl font-semibold text-white truncate drop-shadow-md">
          {movie.title}{" "}
          <span className="text-neutral-400 text-xl font-normal">
            ({movie.year})
          </span>
        </h2>
      </div>

      {/* Video Container */}
      <div className="flex-1 flex justify-center items-center bg-black w-full h-full pt-20">
        <video
          controls
          autoPlay
          className="w-full max-h-screen outline-none shadow-2xl"
          src={getStreamUrl(movie.file_id)}
        >
          Your browser does not support the video tag.
        </video>
      </div>
    </div>
  );
}
