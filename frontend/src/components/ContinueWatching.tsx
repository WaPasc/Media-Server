import { useRef } from "react";
import { type ContinueWatchingItem } from "../api";

interface ContinueWatchingProps {
  items: ContinueWatchingItem[];
  onResume: (fileId: number, title: string, startAt: number) => void;
}

function formatTime(seconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const remainingSeconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(
      remainingSeconds,
    ).padStart(2, "0")}`;
  }

  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

export function ContinueWatching({ items, onResume }: ContinueWatchingProps) {
  const railRef = useRef<HTMLDivElement>(null);

  const scrollRail = (direction: "left" | "right") => {
    const rail = railRef.current;
    if (!rail) {
      return;
    }

    rail.scrollBy({
      left: direction === "left" ? -320 : 320,
      behavior: "smooth",
    });
  };

  if (items.length === 0) {
    return null;
  }

  return (
    <section className="pt-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            Continue Watching
          </h2>
          <p className="text-sm text-neutral-400 mt-1">
            Pick up where you left off.
          </p>
        </div>

        <div className="hidden sm:flex items-center gap-2">
          <button
            type="button"
            onClick={() => scrollRail("left")}
            className="h-9 w-9 rounded-lg border border-neutral-700 bg-neutral-900/70 text-neutral-200 hover:text-white hover:border-neutral-500 transition-colors"
            aria-label="Scroll continue watching left"
          >
            ←
          </button>
          <button
            type="button"
            onClick={() => scrollRail("right")}
            className="h-9 w-9 rounded-lg border border-neutral-700 bg-neutral-900/70 text-neutral-200 hover:text-white hover:border-neutral-500 transition-colors"
            aria-label="Scroll continue watching right"
          >
            →
          </button>
        </div>
      </div>

      <div
        ref={railRef}
        className="flex gap-6 overflow-x-auto pb-2 pr-4 snap-x snap-mandatory [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
        onWheel={(event) => {
          if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) {
            return;
          }

          event.currentTarget.scrollLeft += event.deltaY;
          event.preventDefault();
        }}
      >
        {items.map((item) => {
          const isMovie = item.type === "movie";
          const art = isMovie
            ? item.movie.backdrop_url || item.movie.poster_url
            : item.episode.still_url || item.show.backdrop_url;
          const title = isMovie ? item.movie.title : item.show.title;
          const subtitle = isMovie
            ? item.movie.year
              ? `${item.movie.year}`
              : "Movie"
            : `S${String(item.season_number).padStart(2, "0")}E${String(
                item.episode.episode_number,
              ).padStart(2, "0")} • ${item.episode.title}`;
          const resumeLabel = isMovie
            ? item.movie.title
            : `${item.show.title} - S${String(item.season_number).padStart(
                2,
                "0",
              )}E${String(item.episode.episode_number).padStart(2, "0")}: ${
                item.episode.title
              }`;

          return (
            <button
              type="button"
              key={`${item.type}-${item.file_id}`}
              onClick={() =>
                onResume(item.file_id, resumeLabel, Math.max(0, item.stopped_at))
              }
              className="group w-62.5 shrink-0 text-left snap-start"
            >
              <article className="transform-gpu transition-transform duration-200 ease-out group-hover:scale-[1.02]">
                <div className="relative h-35 w-62.5 bg-neutral-900 rounded-xl overflow-hidden border border-neutral-800 group-hover:border-neutral-600">
                  {art ? (
                    <img
                      src={art}
                      alt={title}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full grid place-items-center text-neutral-500 text-sm">
                      No Image
                    </div>
                  )}

                  <div className="absolute inset-0 bg-linear-to-t from-black/70 via-transparent to-transparent" />

                  <div className="absolute left-0 right-0 bottom-0 h-1 bg-black/30">
                    <div
                      className="h-full bg-indigo-500"
                      style={{
                        width: `${Math.min(100, Math.max(0, item.progress_percentage))}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="pt-2 px-0.5">
                  <h3 className="font-bold text-[15px] text-white truncate">
                    {isMovie ? title : item.show.title}
                  </h3>
                  <p className="text-xs text-neutral-400 truncate mt-0.5">
                    {isMovie
                      ? `${Math.round(item.progress_percentage)}% complete • Resume at ${formatTime(item.stopped_at)}`
                      : `${subtitle} • Resume at ${formatTime(item.stopped_at)}`}
                  </p>
                </div>
              </article>
            </button>
          );
        })}
      </div>
    </section>
  );
}
