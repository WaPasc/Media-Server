import { useQuery } from "@tanstack/react-query";
import { fetchShowDetails, type Media } from "../api";

interface ShowDetailsProps {
  show: Media;
  onBack: () => void;
  onPlay: (fileId: number, title: string) => void;
}

export function ShowDetails({ show, onBack, onPlay }: ShowDetailsProps) {
  const { data: details, isLoading } = useQuery({
    queryKey: ["showDetails", show.id],
    queryFn: () => fetchShowDetails(show.id),
  });

  return (
    <div className="min-h-screen bg-[#09090B] text-white relative overflow-hidden animate-in fade-in duration-500">
      <div className="absolute top-0 left-0 w-full h-[55vh] z-0 select-none pointer-events-none">
        {show.backdrop_url ? (
          <img
            src={show.backdrop_url}
            alt={show.title}
            className="w-full h-full object-cover opacity-30"
          />
        ) : (
          <div className="w-full h-full bg-neutral-900" />
        )}
        <div className="absolute inset-0 bg-linear-to-t from-[#09090B] via-[#09090B]/80 to-transparent" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 sm:px-12 pt-[25vh] pb-20">
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
          {show.title}
        </h1>
        <p className="max-w-3xl text-lg text-neutral-300 leading-relaxed mb-12">
          {show.overview || "No overview available for this show."}
        </p>

        {isLoading ? (
          <div className="flex items-center gap-4 text-indigo-400 font-medium">
            <div className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
            Loading episodes...
          </div>
        ) : (
          <div className="flex flex-col gap-10">
            {details?.seasons.map((season) => (
              <div
                key={season.season_number}
                className="bg-neutral-900/40 p-6 md:p-8 rounded-3xl border border-white/5 shadow-xl"
              >
                <h2 className="text-3xl font-bold mb-6 text-white border-b border-neutral-800 pb-4">
                  Season {season.season_number}
                </h2>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {[...season.episodes]
                    .sort((a, b) => a.episode_number - b.episode_number)
                    .map((episode) => {
                      const isPlayable = !!episode.file_id;
                      return (
                        <div
                          key={episode.episode_number}
                          onClick={() => {
                            if (isPlayable)
                              onPlay(
                                episode.file_id!,
                                `${show.title} - S${season.season_number}E${episode.episode_number}: ${episode.title}`,
                              );
                          }}
                          className={`p-4 rounded-2xl flex gap-4 transition-all duration-200 border ${
                            isPlayable
                              ? "bg-black/40 border-neutral-800 hover:border-neutral-500 cursor-pointer hover:bg-neutral-800/80"
                              : "bg-black/20 border-transparent opacity-50 cursor-not-allowed"
                          }`}
                        >
                          {/* Episode Thumbnail */}
                          <div className="w-32 h-20 shrink-0 bg-neutral-800 rounded-lg overflow-hidden relative">
                            {episode.still_url ? (
                              <img
                                src={episode.still_url}
                                alt={episode.title}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center text-neutral-600 text-xs text-center p-2">
                                No Image
                              </div>
                            )}
                            {isPlayable && (
                              <div className="absolute inset-0 bg-black/20 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                                <svg
                                  className="w-8 h-8 text-white drop-shadow-lg"
                                  fill="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path d="M8 5v14l11-7z" />
                                </svg>
                              </div>
                            )}
                          </div>

                          {/* Episode Metadata */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-sm text-indigo-400 font-bold">
                                Episode {episode.episode_number}
                              </span>
                              {!isPlayable && (
                                <span className="text-[10px] uppercase tracking-wider bg-neutral-800 text-neutral-400 px-2 py-0.5 rounded-full">
                                  Missing File
                                </span>
                              )}
                            </div>
                            <h3 className="font-semibold text-white truncate mb-1">
                              {episode.title}
                            </h3>
                            <p className="text-xs text-neutral-400 line-clamp-2">
                              {episode.overview}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
