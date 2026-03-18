import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { fetchShowDetails, type Media } from "../api";

interface ShowDetailsProps {
  show: Media;
  onBack: () => void;
  onPlay: (fileId: number, title: string) => void;
}

export function ShowDetails({ show, onBack, onPlay }: ShowDetailsProps) {
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);

  const { data: details, isLoading } = useQuery({
    queryKey: ["showDetails", show.id],
    queryFn: () => fetchShowDetails(show.id),
  });

  const sortedSeasons = useMemo(() => {
    return [...(details?.seasons ?? [])].sort(
      (a, b) => a.season_number - b.season_number,
    );
  }, [details]);

  const effectiveSeasonNumber = sortedSeasons.some(
    (season) => season.season_number === selectedSeason,
  )
    ? selectedSeason
    : (sortedSeasons[0]?.season_number ?? null);

  const activeSeason = sortedSeasons.find(
    (season) => season.season_number === effectiveSeasonNumber,
  );

  const sortedEpisodes = useMemo(() => {
    return [...(activeSeason?.episodes ?? [])].sort(
      (a, b) => a.episode_number - b.episode_number,
    );
  }, [activeSeason]);

  return (
    <div className="min-h-screen bg-[#09090B] text-white relative overflow-hidden animate-in fade-in duration-500">
      <div className="absolute inset-0 pointer-events-none">
        {show.backdrop_url ? (
          <img
            src={show.backdrop_url}
            alt={show.title}
            className="h-[55vh] w-full object-cover opacity-25"
          />
        ) : (
          <div className="h-[55vh] w-full bg-neutral-900" />
        )}
        <div className="absolute inset-0 bg-linear-to-t from-[#09090B] via-[#09090B]/75 to-[#09090B]/20" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 sm:px-12 pt-[22vh] pb-20">
        <button
          onClick={onBack}
          className="group mb-8 flex items-center gap-2 text-neutral-300 hover:text-white transition-colors"
        >
          <span className="text-2xl group-hover:-translate-x-1 transition-transform">
            ←
          </span>
          <span className="font-medium">Back to Library</span>
        </button>

        <h1 className="text-5xl md:text-7xl font-extrabold mb-3 tracking-tight text-white">
          {show.title}
        </h1>
        <p className="max-w-3xl text-lg text-neutral-300 leading-relaxed mb-10">
          {show.overview || "No overview available for this show."}
        </p>

        {isLoading ? (
          <div className="flex items-center gap-3 text-indigo-300 font-medium">
            <div className="w-5 h-5 border-2 border-indigo-300 border-t-transparent rounded-full animate-spin" />
            Loading episodes...
          </div>
        ) : (
          <div className="space-y-6">
            <div className="rounded-2xl border border-white/10 bg-neutral-900/60 backdrop-blur-md p-4 sm:p-5">
              <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
                <div>
                  <label
                    htmlFor="season-select"
                    className="block text-xs uppercase tracking-wider text-neutral-400 mb-2"
                  >
                    Season
                  </label>
                  <select
                    id="season-select"
                    value={effectiveSeasonNumber ?? ""}
                    onChange={(event) =>
                      setSelectedSeason(Number(event.target.value))
                    }
                    className="w-full sm:w-72 rounded-xl border border-neutral-700 bg-neutral-950 px-3 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/60"
                  >
                    {sortedSeasons.map((season) => (
                      <option
                        key={season.season_number}
                        value={season.season_number}
                      >
                        Season {season.season_number}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="text-sm text-neutral-400">
                  {sortedEpisodes.length} episode
                  {sortedEpisodes.length === 1 ? "" : "s"}
                </div>
              </div>
            </div>

            {!activeSeason ? (
              <div className="text-neutral-400">No season data available.</div>
            ) : (
              <div className="rounded-3xl border border-white/10 bg-neutral-900/45 p-5 sm:p-6">
                <h2 className="text-2xl font-semibold text-white mb-5">
                  Season {activeSeason.season_number}
                </h2>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {sortedEpisodes.map((episode) => {
                    const isPlayable = episode.file_id !== null;
                    const thumb = episode.still_url || show.backdrop_url;
                    const label = `${show.title} - S${String(
                      activeSeason.season_number,
                    ).padStart(2, "0")}E${String(
                      episode.episode_number,
                    ).padStart(2, "0")}: ${episode.title}`;

                    return (
                      <button
                        key={episode.episode_number}
                        type="button"
                        onClick={() => {
                          if (episode.file_id !== null) {
                            onPlay(episode.file_id, label);
                          } else {
                            window.alert(
                              "No file attached for this episode yet.",
                            );
                          }
                        }}
                        className={`group text-left rounded-2xl border overflow-hidden transition-all ${
                          isPlayable
                            ? "border-neutral-700 bg-black/40 hover:bg-neutral-900 hover:border-indigo-500"
                            : "border-neutral-800 bg-black/25 hover:border-neutral-600"
                        }`}
                      >
                        <div className="flex gap-4 p-4">
                          <div className="w-36 h-20 rounded-lg overflow-hidden shrink-0 bg-neutral-800">
                            {thumb ? (
                              <img
                                src={thumb}
                                alt={episode.title}
                                className="w-full h-full object-cover"
                                loading="lazy"
                              />
                            ) : (
                              <div className="h-full w-full grid place-items-center text-[11px] text-neutral-500">
                                No Image
                              </div>
                            )}
                          </div>

                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-bold tracking-wide text-indigo-400">
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
                              {episode.overview || "No description available."}
                            </p>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
