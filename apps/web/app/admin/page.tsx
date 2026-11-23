"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, clearSession, getStoredUser, getToken } from "@/lib/api";
import type { AdminOrder, Listing } from "@/lib/types";

type Metrics = {
  textbooks: number;
  active_listings: number;
  completed_orders: number;
};

const LISTING_STATUS_LABELS: Record<string, string> = {
  active: "在售",
  removed: "已下架",
  reserved: "已预留",
  sold: "已售出",
};

const ORDER_STATUS_LABELS: Record<string, string> = {
  pending_payment: "待支付",
  paid: "已支付，待交接",
  completed: "已完成",
  cancelled: "已取消",
  refunded: "已退款",
};

export default function AdminPage() {
  const router = useRouter();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [listingFilter, setListingFilter] = useState("");
  const [orderFilter, setOrderFilter] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");
  const [loading, setLoading] = useState(true);

  const redirectToLogin = useCallback(() => {
    clearSession();
    router.replace("/login");
  }, [router]);

  const load = useCallback(async () => {
    const token = getToken();
    const user = getStoredUser();
    if (!token || user?.role !== "admin") {
      redirectToLogin();
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [metricsData, listingData, orderData] = await Promise.all([
        api.adminMetrics(token),
        api.adminListings(token, listingFilter),
        api.adminOrders(token, orderFilter),
      ]);
      setMetrics(metricsData);
      setListings(listingData);
      setOrders(orderData);
    } catch (caught) {
      if (caught instanceof Error && "status" in caught) {
        const status = (caught as { status: number }).status;
        if (status === 401 || status === 403) {
          redirectToLogin();
          return;
        }
      }
      setError(caught instanceof Error ? caught.message : "运营数据加载失败。");
    } finally {
      setLoading(false);
    }
  }, [listingFilter, orderFilter, redirectToLogin]);

  useEffect(() => {
    void load();
  }, [load]);

  const moderate = async (listing: Listing, next: "active" | "removed") => {
    const token = getToken();
    if (!token) {
      redirectToLogin();
      return;
    }
    let reason = "管理员恢复上架";
    if (next === "removed") {
      const input = window.prompt(
        `下架《${listing.textbook_title}》的原因（可留空）`,
        "不符合校园教材循环规范",
      );
      if (input === null) return;
      reason = input.trim();
    }
    setBusy(listing.id);
    setError("");
    setMessage("");
    try {
      await api.moderateListing(token, listing.id, next, reason);
      setMessage(
        next === "removed"
          ? `已下架《${listing.textbook_title}》`
          : `已恢复《${listing.textbook_title}》`,
      );
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "审核操作失败。");
    } finally {
      setBusy("");
    }
  };

  const refund = async (order: AdminOrder) => {
    const token = getToken();
    if (!token) {
      redirectToLogin();
      return;
    }
    const input = window.prompt(
      `退款订单 ${order.id.slice(0, 8)} 的原因`,
      "管理员沙箱退款",
    );
    if (input === null) return;
    const reason = input.trim();
    if (reason.length < 2) {
      setError("退款原因至少需要 2 个字符。");
      return;
    }
    setBusy(order.id);
    setError("");
    setMessage("");
    try {
      await api.refundOrder(token, order.id, reason);
      setMessage(`订单 ${order.id.slice(0, 8)} 已退款，书籍恢复在售。`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "退款失败。");
    } finally {
      setBusy("");
    }
  };

  return (
    <main className="page-shell py-12">
      <p className="eyebrow">演示运营台</p>
      <h1 className="display-title mt-2 text-5xl font-black">平台脉搏</h1>
      <p className="mt-4 max-w-2xl leading-7 text-fog">
        指标从数据库实时复算。书籍下架、恢复和沙箱退款都会写入审计事件，不展示虚构用户量或交易额。
      </p>

      {error ? (
        <div className="mt-6 border-l-4 border-brick bg-white/70 px-4 py-3 text-sm text-brick">
          {error}
        </div>
      ) : null}
      {message ? (
        <div className="mt-6 border-l-4 border-moss bg-white/70 px-4 py-3 text-sm text-moss">
          {message}
        </div>
      ) : null}

      <div className="mt-8 grid gap-px border border-ink/20 bg-ink/20 sm:grid-cols-3">
        {[
          ["教材条目", metrics?.textbooks],
          ["在售书籍", metrics?.active_listings],
          ["已完成订单", metrics?.completed_orders],
        ].map(([label, value]) => (
          <div className="bg-chalk p-7" key={String(label)}>
            <p className="display-title text-5xl font-black">{value ?? "…"}</p>
            <p className="mt-3 text-sm text-fog">{label}</p>
          </div>
        ))}
      </div>

      <section className="mt-10" aria-labelledby="moderation-title">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="eyebrow">内容治理</p>
            <h2 id="moderation-title" className="display-title mt-2 text-3xl font-bold">
              书籍审核
            </h2>
          </div>
          <label className="text-xs font-semibold text-fog">
            状态
            <select
              className="field mt-1.5"
              value={listingFilter}
              onChange={(event) => setListingFilter(event.target.value)}
            >
              <option value="">全部</option>
              {Object.entries(LISTING_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4 space-y-3">
          {loading ? (
            <p className="py-10 text-center text-fog">正在读取运营数据…</p>
          ) : listings.length ? (
            listings.map((listing) => (
              <article
                className="grid gap-4 border border-ink/20 bg-chalk/80 p-4 md:grid-cols-[1fr_auto] md:items-center"
                key={listing.id}
              >
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="status-pill">
                      {LISTING_STATUS_LABELS[listing.status] ?? listing.status}
                    </span>
                    <span className="text-xs text-fog">
                      {listing.condition_grade} 成新 · ¥{listing.asking_price.toFixed(0)}
                    </span>
                  </div>
                  <h3 className="mt-2 font-display text-xl font-bold">{listing.textbook_title}</h3>
                  <p className="mt-1 text-sm text-fog">
                    {listing.course_name} · 卖家 {listing.seller_name} ·{" "}
                    {new Date(listing.created_at).toLocaleString("zh-CN")}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {listing.status === "active" ? (
                    <button
                      className="secondary-button min-h-9 px-3 py-1.5 text-xs"
                      disabled={busy === listing.id}
                      onClick={() => moderate(listing, "removed")}
                      type="button"
                    >
                      下架
                    </button>
                  ) : null}
                  {listing.status === "removed" ? (
                    <button
                      className="primary-button min-h-9 px-3 py-1.5 text-xs"
                      disabled={busy === listing.id}
                      onClick={() => moderate(listing, "active")}
                      type="button"
                    >
                      恢复
                    </button>
                  ) : null}
                  {listing.status === "reserved" || listing.status === "sold" ? (
                    <span className="text-xs text-fog">订单占用中</span>
                  ) : null}
                </div>
              </article>
            ))
          ) : (
            <p className="border border-dashed border-ink/30 px-4 py-10 text-center text-fog">
              当前筛选下没有书籍。
            </p>
          )}
        </div>
      </section>

      <section className="mt-12" aria-labelledby="refund-title">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="eyebrow">沙箱售后</p>
            <h2 id="refund-title" className="display-title mt-2 text-3xl font-bold">
              退款管理
            </h2>
          </div>
          <label className="text-xs font-semibold text-fog">
            状态
            <select
              className="field mt-1.5"
              value={orderFilter}
              onChange={(event) => setOrderFilter(event.target.value)}
            >
              <option value="">全部</option>
              {Object.entries(ORDER_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4 space-y-3">
          {loading ? (
            <p className="py-10 text-center text-fog">正在读取订单…</p>
          ) : orders.length ? (
            orders.map((order) => (
              <article
                className="grid gap-4 border border-ink/20 bg-chalk/80 p-4 md:grid-cols-[1fr_auto] md:items-center"
                key={order.id}
              >
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="status-pill">
                      {ORDER_STATUS_LABELS[order.status] ?? order.status}
                    </span>
                    <span className="text-xs text-fog">
                      {new Date(order.created_at).toLocaleString("zh-CN")}
                    </span>
                  </div>
                  <h3 className="mt-2 font-display text-xl font-bold">{order.textbook_title}</h3>
                  <p className="mt-1 text-sm text-fog">
                    买家 {order.buyer_name} → 卖家 {order.seller_name} · 成交 ¥
                    {order.amount.toFixed(2)} · 佣金 ¥{order.commission_amount.toFixed(2)}
                  </p>
                  <p className="mt-1 break-all text-[10px] text-fog">订单 {order.id}</p>
                </div>
                <div>
                  {order.status === "paid" ? (
                    <button
                      className="secondary-button min-h-9 px-3 py-1.5 text-xs"
                      disabled={busy === order.id}
                      onClick={() => refund(order)}
                      type="button"
                    >
                      退款
                    </button>
                  ) : (
                    <span className="text-xs text-fog">无可用操作</span>
                  )}
                </div>
              </article>
            ))
          ) : (
            <p className="border border-dashed border-ink/30 px-4 py-10 text-center text-fog">
              当前筛选下没有订单。
            </p>
          )}
        </div>
      </section>
    </main>
  );
}
