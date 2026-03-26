import { useRef } from "react";
import { getStreamUrl } from "../api";


interface VideoPlayerProps {
  fileId: number;
  title: string;
  onBack: () => void;
  startAt?: number;
}

export function VideoPlayer({
  fileId,
  title,
  onBack,
  startAt = 0,
}: VideoPlayerProps) {
  const hasSeeked = useRef(false);

  return (
    <div className="min-h-screen bg-black flex flex-col relative animate-in zoom-in-95 duration-300">
      <div className="p-6 flex items-center gap-6 absolute top-0 left-0 w-full z-10 bg-linear-to-b from-black/90 to-transparent">
        <button
          onClick={onBack}
          className="group flex items-center gap-2 px-4 py-2 text-neutral-400 hover:text-white transition-colors"
        >
          <span className="text-2xl group-hover:-translate-x-1 transition-transform">←</span>
          <span className="font-medium text-lg">Stop Playback</span>
        </button>
        <h2 className="text-2xl font-semibold text-white drop-shadow-md truncate">
          {title}
        </h2>
      </div>

      <div className="flex-1 flex justify-center items-center w-full h-full pt-20 pb-10 px-4 md:px-10">
        <video
          controls
          autoPlay
          className="w-full max-h-[85vh] rounded-xl shadow-2xl shadow-indigo-500/10 ring-1 ring-white/10"
          src={getStreamUrl(fileId)}
          onLoadedMetadata={(event) => {
            if (hasSeeked.current || startAt <= 0) {
              return;
            }

            const video = event.currentTarget;
            video.currentTime = Math.min(startAt, video.duration || startAt);
            hasSeeked.current = true;
          }}
        />
      </div>
    </div>
  );
}