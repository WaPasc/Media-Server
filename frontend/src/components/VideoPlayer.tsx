import { type Movie, getStreamUrl } from "../api";

interface VideoPlayerProps {
  movie: Movie;
  onBack: () => void;
}

export default function VideoPlayer({ movie, onBack }: VideoPlayerProps) {
  if (!movie.file_id) {
    return (
      <div className="min-h-screen bg-[#09090B] text-white flex flex-col items-center justify-center p-6 text-center">
        <h2 className="text-3xl font-bold mb-4 text-rose-500">
          Media Not Found
        </h2>
        <p className="text-neutral-400 mb-8 max-w-md">
          No physical file is attached to "{movie.title}".
        </p>
        <button
          onClick={onBack}
          className="px-6 py-3 bg-neutral-800 hover:bg-neutral-700 rounded-lg transition-colors"
        >
          Back to Library
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black flex flex-col relative">
      <div className="p-6 flex items-center gap-6 absolute top-0 left-0 w-full z-10 bg-linear-to-b from-black/90 to-transparent">
        <button
          onClick={onBack}
          className="group flex items-center gap-2 px-4 py-2 text-neutral-400 hover:text-white transition-colors"
        >
          <span className="text-2xl group-hover:-translate-x-1 transition-transform">
            ←
          </span>
          <span className="font-medium text-lg">Back</span>
        </button>
        <h2 className="text-2xl font-semibold text-white drop-shadow-md truncate">
          {movie.title}{" "}
          <span className="text-neutral-400 font-normal">({movie.year})</span>
        </h2>
      </div>

      <div className="flex-1 flex justify-center items-center w-full h-full pt-20 pb-10 px-10">
        <video
          controls
          autoPlay
          className="w-full max-h-[85vh] rounded-xl shadow-2xl shadow-indigo-500/10 ring-1 ring-white/10"
          src={getStreamUrl(movie.file_id)}
        />
      </div>
    </div>
  );
}
