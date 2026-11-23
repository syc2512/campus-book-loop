"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { PriceEstimate } from "@/lib/types";

const INITIAL_RESULT: PriceEstimate = {
  suggested_price: 25.5,
  low_price: 22.95,
  high_price: 28.05,
  source: "preview",
  model_version: "preview",
  factors: { condition: 0.62, category: 1.08, demand: 1.0 },
  disclaimer: "输入新书价格和品相后获取估价。",
};

export function PriceEstimator() {
  const [newPrice, setNewPrice] = useState(68);
  const [condition, setCondition] = useState(8);
  const [category, setCategory] = useState("专业课");
  const [demand, setDemand] = useState(1);
  const [hasNotes, setHasNotes] = useState(false);
  const [result, setResult] = useState<PriceEstimate>(INITIAL_RESULT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setResult((current) => ({
      ...current,
      suggested_price: Math.round(newPrice * (0.12 + condition * 0.058) * 100) / 100,
    }));
  }, [newPrice, condition]);

  const estimate = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.estimatePrice({
        new_price: newPrice,
        condition_grade: condition,
        category,
        demand_factor: demand,
        has_notes: hasNotes,
        edition_current: true,
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "估价服务暂时不可用。");
    } finally {
      setLoading(false);
    }
  };

  const maxMark = Math.max(result.high_price, result.suggested_price) * 1.18;
  const left = (result.low_price / maxMark) * 100;
  const width = ((result.high_price - result.low_price) / maxMark) * 100;
  const marker = (result.suggested_price / maxMark) * 100;

  return (
    <aside className="relative paper-panel p-5 sm:p-6">
      <div className="absolute -right-3 top-10 rotate-3 border-2 border-brick px-3 py-1 text-xs font-bold text-brick">
        合成模型试算
      </div>
      <div className="border-b border-dashed border-ink/30 pb-4">
        <p className="eyebrow">价格雷达</p>
        <h2 className="display-title mt-2 text-3xl font-bold">这张旧书值多少</h2>
        <p className="mt-2 text-sm leading-6 text-fog">
          规则基线负责托底，合成模型展示完整推理管线。
        </p>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <label className="text-xs font-semibold text-fog">
          新书原价
          <input
            className="field mt-1.5"
            min="1"
            max="5000"
            type="number"
            value={newPrice}
            onChange={(event) => setNewPrice(Number(event.target.value) || 1)}
          />
        </label>
        <label className="text-xs font-semibold text-fog">
          品相
          <select
            className="field mt-1.5"
            value={condition}
            onChange={(event) => setCondition(Number(event.target.value))}
          >
            {Array.from({ length: 10 }, (_, index) => 10 - index).map((grade) => (
              <option key={grade} value={grade}>
                {grade} 成新
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold text-fog">
          教材类型
          <select
            className="field mt-1.5"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            <option>公共课</option>
            <option>专业课</option>
            <option>考研资料</option>
            <option>笔记/真题</option>
          </select>
        </label>
        <label className="text-xs font-semibold text-fog">
          需求热度
          <select
            className="field mt-1.5"
            value={demand}
            onChange={(event) => setDemand(Number(event.target.value))}
          >
            <option value={0.8}>冷门</option>
            <option value={1}>正常</option>
            <option value={1.2}>热门</option>
            <option value={1.4}>开学季</option>
          </select>
        </label>
      </div>

      <label className="mt-4 flex cursor-pointer items-center gap-2 text-sm">
        <input
          checked={hasNotes}
          className="h-4 w-4 accent-moss"
          type="checkbox"
          onChange={(event) => setHasNotes(event.target.checked)}
        />
        书内有较多笔记或划线
      </label>

      <div className="mt-5 border-y border-ink/20 py-4">
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold text-fog">建议成交价</p>
            <p className="display-title mt-1 text-5xl font-black">¥{result.suggested_price.toFixed(2)}</p>
          </div>
          <div className="text-right text-sm">
            <p className="text-fog">合理区间</p>
            <p className="mt-1 font-bold">
              ¥{result.low_price.toFixed(0)}—{result.high_price.toFixed(0)}
            </p>
          </div>
        </div>
        <div className="relative mt-5 h-8 border-l border-r border-ink/25 bg-white/60">
          <div
            className="absolute inset-y-0 bg-marigold/75"
            style={{ left: `${Math.min(left, 100)}%`, width: `${Math.min(width, 100)}%` }}
          />
          <div
            className="absolute -top-2 h-12 w-0.5 bg-brick"
            style={{ left: `${Math.min(marker, 100)}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-fog">
          <span>保留</span>
          <span>容易成交</span>
        </div>
      </div>

      <button
        className="primary-button mt-5 w-full disabled:cursor-wait disabled:opacity-60"
        disabled={loading}
        onClick={estimate}
        type="button"
      >
        {loading ? "正在计算…" : "生成估价依据"}
      </button>
      {error ? <p className="mt-3 text-sm text-brick">{error}</p> : null}
      {!error ? (
        <p className="mt-3 text-[11px] leading-5 text-fog">
          {result.source === "synthetic_price_model"
            ? `模型：${result.model_version}。`
            : "当前为前端预览，连接 API 后显示模型结果。"}
          {result.disclaimer}
        </p>
      ) : null}
    </aside>
  );
}
