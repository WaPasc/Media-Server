import { useState } from "react";
import { type Media } from "../api";

interface MediaGridProps {
  items: Media[];
  onItemClick: (item: Media) => void;
  activeTab: "movies" | "shows";
}

export function MediaGrid({ items, onItemClick, activeTab }: MediaGridProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredItems = items.filter((item) =>
    item.title.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="p-6 md:p-12">
      <div className="mb-8">
        <input
          type="text"
          placeholder={`Search ${activeTab}...`}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-md px-5 py-3 bg-neutral-900 border border-neutral-800 rounded-xl text-white placeholder-neutral-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all shadow-inner"
        />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
        {filteredItems.map((item) => (
          <div
            key={item.id}
            onClick={() => onItemClick(item)}
            className="group relative cursor-pointer transition-all duration-300 hover:scale-105 hover:z-10"
          >
            <div className="aspect-2/3 w-full bg-neutral-900 rounded-xl shadow-lg overflow-hidden border border-neutral-800 group-hover:border-neutral-600 group-hover:shadow-purple-500/20 transition-all">
              {item.poster_url ? (
                <img
                  src={item.poster_url}
                  alt={item.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-neutral-600 text-sm p-4 text-center">
                  No Poster
                </div>
              )}
            </div>
            <div className="mt-3 px-1">
              <h3 className="text-sm md:text-base font-semibold text-neutral-100 truncate">
                {item.title}
              </h3>
              <p className="text-xs text-neutral-500 font-medium">
                {item.year || "Unknown Year"}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
