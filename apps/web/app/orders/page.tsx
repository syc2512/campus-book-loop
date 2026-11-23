"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, getToken } from "@/lib/api";
import type { Order } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  pending_payment: "待支付",
  paid: "已支付，待交接",
  completed: "已完成",
  cancelled: "已取消",
  refunded: "已退款",
};

export default function OrdersPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    setLoading(true);
    try {
      setOrders(await api.orders(token));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "订单加载失败。");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const act = async (order: Order, action: "complete" | "cancel") => {
    const token = getToken();
    if (!token) return;
    setBusy(order.id);
    setError("");
    try {
      if (action === "complete") await api.completeOrder(token, order.id);
      else await api.cancelOrder(token, order.id);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "操作失败。");
    } finally {
      setBusy("");
    }
  };

  return (
    <main className="page-shell py-12">
      <div className="flex flex-col justify-between gap-4 border-b border-ink/20 pb-8 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow">交接记录</p>
          <h1 className="display-title mt-2 text-5xl font-black">我的订单</h1>
        </div>
        <p className="max-w-lg text-sm leading-6 text-fog">
          这里展示买家与卖家相关订单。支付为沙箱状态，不产生真实资金流。
        </p>
      </div>

      {error ? <div className="mt-6 border-l-4 border-brick bg-white/70 px-4 py-3 text-sm text-brick">{error}</div> : null}

      <div className="mt-8 space-y-4">
        {loading ? (
          <p className="py-20 text-center text-fog">正在读取交接记录…</p>
        ) : orders.length ? (
          orders.map((order) => (
            <article
              className="grid gap-5 border border-ink/20 bg-chalk/80 p-5 md:grid-cols-[1fr_auto] md:items-center"
              key={order.id}
            >
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <span className="status-pill">{STATUS_LABELS[order.status] ?? order.status}</span>
                  <span className="text-xs text-fog">{new Date(order.created_at).toLocaleString("zh-CN")}</span>
                </div>
                <h2 className="mt-3 font-display text-2xl font-bold">{order.textbook_title}</h2>
                <p className="mt-2 text-sm text-fog">
                  成交价 ¥{order.amount.toFixed(2)} · 演示佣金 ¥{order.commission_amount.toFixed(2)}
                </p>
                <p className="mt-1 break-all text-[10px] text-fog">订单 {order.id}</p>
              </div>
              <div className="flex gap-2">
                {order.status === "paid" ? (
                  <button
                    className="primary-button min-h-9 px-4 py-1.5"
                    disabled={busy === order.id}
                    onClick={() => act(order, "complete")}
                    type="button"
                  >
                    确认交接
                  </button>
                ) : null}
                {order.status === "pending_payment" ? (
                  <button
                    className="secondary-button min-h-9 px-4 py-1.5"
                    disabled={busy === order.id}
                    onClick={() => act(order, "cancel")}
                    type="button"
                  >
                    取消订单
                  </button>
                ) : null}
              </div>
            </article>
          ))
        ) : (
          <div className="border border-dashed border-ink/30 px-6 py-20 text-center">
            <p className="font-display text-2xl font-bold">还没有订单</p>
            <p className="mt-2 text-sm text-fog">回到教材索引，用另一个演示账号完成一次沙箱下单。</p>
          </div>
        )}
      </div>
    </main>
  );
}
