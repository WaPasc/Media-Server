// frontend/src/api.ts

export interface Media {
  id: number;
  title: string;
  year: number | null;
  overview: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
}

export interface Movie extends Media {
  file_id: number | null;
}

export type Show = Media;

export interface ShowDetails extends Media {
  seasons: Season[];
}

export interface Season {
  season_number: number;
  episodes: Episode[];
}

export interface Episode {
  episode_number: number;
  title: string;
  overview: string | null;
  still_url: string | null;
  file_id: number | null;
}

interface ContinueWatchingBase {
  file_id: number;
  stopped_at: number;
  duration: number | null;
  progress_percentage: number;
  updated_at: string;
}

export interface ContinueWatchingMovie extends ContinueWatchingBase {
  type: "movie";
  movie: Movie;
}

export interface ContinueWatchingEpisode extends ContinueWatchingBase {
  type: "episode";
  show: Show;
  episode: Episode;
  season_number: number;
}

export type ContinueWatchingItem =
  | ContinueWatchingMovie
  | ContinueWatchingEpisode;

const API_BASE_URL = "http://127.0.0.1:8000/api";

export const fetchMovies = async (): Promise<Movie[]> => {
  const response = await fetch(`${API_BASE_URL}/movies`);
  if (!response.ok) throw new Error("Failed to fetch movies");
  return await response.json();
};

export const fetchShows = async (): Promise<Show[]> => {
  const response = await fetch(`${API_BASE_URL}/shows`);
  if (!response.ok) throw new Error("Failed to fetch shows");
  return await response.json();
};

export const fetchShowDetails = async (
  show_id: number,
): Promise<ShowDetails> => {
  const response = await fetch(`${API_BASE_URL}/show/${show_id}`);
  if (!response.ok) throw new Error("Failed to fetch show details");
  return await response.json();
};

export const fetchContinueWatching = async (): Promise<
  ContinueWatchingItem[]
> => {
  const response = await fetch(`${API_BASE_URL}/continue-watching`);
  if (!response.ok) throw new Error("Failed to fetch continue watching");
  return await response.json();
};

export const getStreamUrl = (fileId: number): string => {
  return `${API_BASE_URL}/stream/${fileId}`;
};