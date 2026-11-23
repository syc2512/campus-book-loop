"use client";

import { BookCover } from "@/components/BookCover";
import { resolveAssetUrl } from "@/lib/api";
import type { Listing } from "@/lib/types";

export function ListingCard({
  listing,
  busy,
  onBuy,
}: {
  listing: Listing;
  busy: boolean;
  onBuy: (listing: Listing) => void;
}) {
  const discount = Math.round((listing.asking_price / listing.new_price) * 100);
  const imageUrl = resolveAssetUrl(listing.image_url);

  return (
    <article className="group grid grid-cols-[88px_1fr] gap-4 border-t border-ink/20 py-5">
      {imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          alt={`${listing.textbook_title} 实拍图`}
          className="h-32 w-[88px] border border-ink/15 bg-white/70 object-cover"
          src={imageUrl}
        />
      ) : (
        <BookCover compact code={listing.course_name.slice(0, 8)} title={listing.textbook_title} />
      )}
      <div className="min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold text-moss">
              {listing.course_name} · {listing.edition}
            </p>
            <h3 className="mt-1 font-display text-xl font-bold leading-snug">
              {listing.textbook_title}
            </h3>
          </div>
          <span className="status-pill shrink-0">{listing.condition_grade} 成新</span>
        </div>
        <p className="mt-2 line-clamp-2 text-sm leading-6 text-fog">{listing.note}</p>
        <div className="mt-4 flex items-end justify-between gap-3">
          <div>
            <p className="display-title text-2xl font-black">¥{listing.asking_price.toFixed(0)}</p>
            <p className="mt-0.5 text-[11px] text-fog">
              原价 ¥{listing.new_price.toFixed(0)} · {discount} 折
            </p>
          </div>
          <button
            className="secondary-button min-h-9 px-3 py-1.5 text-xs"
            disabled={busy}
            onClick={() => onBuy(listing)}
            type="button"
          >
            {busy ? "处理中" : "走沙箱下单"}
          </button>
        </div>
      </div>
    </article>
  );
}
