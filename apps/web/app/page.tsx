"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { BookCover } from "@/components/BookCover";
import { ListingCard } from "@/components/ListingCard";
import { PriceEstimator } from "@/components/PriceEstimator";
import { api, clearSession, getStoredUser, getToken } from "@/lib/api";
import type { Listing, RecommendationItem } from "@/lib/types";

export default function HomePage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyListing, setBusyListing] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async (term = "") => {
    setLoading(true);
    setMessage("");
    try {
      const [listingData, recommendationData] = await Promise.all([
        api.listings(term),
        api.recommendations(),
      ]);
      setListings(listingData);
      setRecommendations(recommendationData.items);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "暂时无法加载教材。");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const search = (event: React.FormEvent) => {
    event.preventDefault();
    void load(query.trim());
  };

  const buy = async (listing: Listing) => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    const user = getStoredUser();
    if (user?.id === listing.seller_id) {
      setMessage("这是你自己发布的教材，换一个账号体验购买流程。");
      return;
    }

    setBusyListing(listing.id);
    setMessage("");
    try {
      const key =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `demo-${Date.now()}`;
      const order = await api.createOrder(token, listing.id, key);
      await api.payOrder(token, order.id);
      router.push("/orders");
    } catch (error) {
      if (error instanceof Error && "status" in error && (error as { status: number }).status === 401) {
        clearSession();
        router.push("/login");
        return;
      }
      setMessage(error instanceof Error ? error.message : "下单失败。");
    } finally {
      setBusyListing("");
    }
  };

  const minPrice = listings.length ? Math.min(...listings.map((item) => item.asking_price)) : 0;

  return (
    <main>
      <section className="overflow-hidden border-b border-ink/20">
        <div className="page-shell grid gap-10 py-12 lg:grid-cols-[1.25fr_0.75fr] lg:items-center lg:py-20">
          <div className="relative">
            <p className="eyebrow">把教材留在校园里</p>
            <h1 className="display-title mt-5 max-w-[760px] text-[clamp(3.2rem,8vw,7.5rem)] font-black leading-[0.94]">
              让一本书
              <br />
              找到下一届。
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-fog sm:text-lg">
              查课程对应教材，看品相和价格依据，再完成一次可追踪的校园交接。
              AI 估价与推荐在这里都有基线、实验和明确的适用边界。
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a className="primary-button" href="#catalog">
                浏览正在流转的教材
              </a>
              <Link className="secondary-button" href="/publish">
                发布一本旧书
              </Link>
            </div>
            <div className="mt-10 grid max-w-2xl grid-cols-3 border-y border-ink/20 py-4">
              <div>
                <p className="display-title text-3xl font-black">{listings.length}</p>
                <p className="mt-1 text-xs text-fog">在售条目</p>
              </div>
              <div className="border-l border-ink/20 pl-5">
                <p className="display-title text-3xl font-black">
                  {minPrice ? `¥${minPrice.toFixed(0)}` : "—"}
                </p>
                <p className="mt-1 text-xs text-fog">当前最低价</p>
              </div>
              <div className="border-l border-ink/20 pl-5">
                <p className="display-title text-3xl font-black">2</p>
                <p className="mt-1 text-xs text-fog">AI 实验任务</p>
              </div>
            </div>
          </div>
          <PriceEstimator />
        </div>
      </section>

      <section className="page-shell py-12 lg:py-16" aria-labelledby="recommendation-title">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="eyebrow">当前供给雷达</p>
            <h2 id="recommendation-title" className="display-title mt-2 text-4xl font-bold">
              不只按热度推荐
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-fog">
            首版使用内容相似度、同课程和供给活跃度的可解释基线；协同过滤将在真实行为数据足够后加入。
          </p>
        </div>
        <div className="mt-7 grid gap-px overflow-hidden border border-ink/20 bg-ink/20 md:grid-cols-3">
          {recommendations.slice(0, 6).map((item, index) => (
            <article
              className="flex min-h-44 gap-4 bg-chalk p-5"
              key={item.textbook.id}
            >
              <span className="display-title text-3xl font-black text-ink/20">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <p className="text-xs font-semibold text-brick">{item.reason}</p>
                <h3 className="mt-2 font-display text-xl font-bold leading-snug">
                  {item.textbook.title}
                </h3>
                <p className="mt-3 text-sm text-fog">
                  {item.available_count} 本在售 · 最低 ¥{item.lowest_price.toFixed(0)}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section id="catalog" className="border-y border-ink/20 bg-chalk/55 py-12 lg:py-16">
        <div className="page-shell">
          <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr] lg:items-end">
            <div>
              <p className="eyebrow">教材索引</p>
              <h2 className="display-title mt-2 text-4xl font-bold">按课程、书名或 ISBN 找</h2>
            </div>
            <form className="flex gap-2" onSubmit={search}>
              <label className="sr-only" htmlFor="catalog-search">
                搜索教材
              </label>
              <input
                id="catalog-search"
                className="field"
                placeholder="例如：机器学习、AI201、9787111695851"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <button className="primary-button shrink-0" type="submit">
                查找
              </button>
            </form>
          </div>

          {message ? (
            <div className="mt-6 border-l-4 border-brick bg-white/75 px-4 py-3 text-sm text-brick">
              {message}
            </div>
          ) : null}

          <div className="mt-8 grid gap-x-10 lg:grid-cols-2">
            {loading ? (
              <div className="col-span-2 py-16 text-center text-fog">正在整理书架…</div>
            ) : listings.length ? (
              listings.map((listing) => (
                <ListingCard
                  key={listing.id}
                  busy={busyListing === listing.id}
                  listing={listing}
                  onBuy={buy}
                />
              ))
            ) : (
              <div className="col-span-2 border border-dashed border-ink/30 px-6 py-16 text-center">
                <p className="font-display text-2xl font-bold">还没有匹配的教材</p>
                <p className="mt-2 text-sm text-fog">换一个课程名、书名或 ISBN 再试。</p>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="page-shell grid gap-8 py-12 lg:grid-cols-[0.8fr_1.2fr] lg:py-20">
        <div className="paper-panel flex items-center justify-center p-8">
          <div className="grid grid-cols-2 gap-5">
            <div className="-rotate-3">
              <BookCover code="AI201" title="机器学习" />
            </div>
            <div className="mt-10 rotate-3">
              <BookCover code="CS202" title="数据结构" />
            </div>
          </div>
        </div>
        <div className="flex flex-col justify-center">
          <p className="eyebrow">项目边界</p>
          <h2 className="display-title mt-3 text-4xl font-bold leading-tight sm:text-5xl">
            先证明闭环，
            <br />
            再增加 AI 复杂度。
          </h2>
          <p className="mt-5 max-w-2xl leading-8 text-fog">
            API、支付和订单采用演示沙箱；估价模型使用合成数据并标记来源；不接入真实教务系统，不保存真实学生隐私。
            作品集展示的是工程判断、评估方法和可复现结果。
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link className="secondary-button" href="/publish">
              发布并估价
            </Link>
            <a className="secondary-button" href="http://localhost:8000/docs" target="_blank">
              查看 API 文档
            </a>
          </div>
        </div>
      </section>
    </main>
  );
}
