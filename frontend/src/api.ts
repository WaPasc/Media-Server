// frontend/src/api.ts

export interface Movie {
    id: number;
    title: string;
    year: number | null;
    overview: string | null;
    poster_url: string | null;
    backdrop_url: string | null;
    file_id: number | null;
}

const API_BASE_URL = 'http://127.0.0.1:8000/api';

export const fetchMovies = async (): Promise<Movie[]> => {
    const response = await fetch(`${API_BASE_URL}/movies`);
    if (!response.ok) throw new Error('Failed to fetch movies');
    return await response.json();
};

export const getStreamUrl = (fileId: number): string => {
    return `${API_BASE_URL}/stream/${fileId}`;
};