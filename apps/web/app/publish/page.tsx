"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, getToken } from "@/lib/api";
import type { PriceEstimate, Textbook } from "@/lib/types";

export default function PublishPage() {
  const router = useRouter();
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [textbookId, setTextbookId] = useState("");
  const [condition, setCondition] = useState(8);
  const [price, setPrice] = useState(20);
  const [note, setNote] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState("");
  const [estimate, setEstimate] = useState<PriceEstimate | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api
      .textbooks()
      .then((items) => {
        setTextbooks(items);
        if (items[0]) setTextbookId(items[0].id);
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "教材加载失败。"));
  }, [router]);

  const selected = textbooks.find((item) => item.id === textbookId);

  const calculate = async () => {
    if (!selected) return;
    setError("");
    try {
      const result = await api.estimatePrice({
        new_price: selected.new_price,
        condition_grade: condition,
        category: selected.category,
        demand_factor: 1,
        has_notes: note.includes("笔记") || note.includes("划线"),
        edition_current: true,
      });
      setEstimate(result);
      setPrice(result.suggested_price);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "估价失败。");
    }
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    setLoading(true);
    setError("");
    try {
      let imageUrl: string | null = null;
      if (imageFile) {
        const uploaded = await api.uploadListingImage(token, imageFile);
        imageUrl = uploaded.image_url;
      }
      await api.createListing(token, {
        textbook_id: textbookId,
        condition_grade: condition,
        asking_price: price,
        note,
        image_url: imageUrl,
      });
      router.push("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "发布失败。");
    } finally {
      setLoading(false);
    }
  };

  const pickImage = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setImageFile(file);
    setImagePreview(file ? URL.createObjectURL(file) : "");
  };

  return (
    <main className="page-shell grid gap-10 py-12 lg:grid-cols-[1fr_0.8fr] lg:items-start">
      <section>
        <p className="eyebrow">发布旧书</p>
        <h1 className="display-title mt-3 text-5xl font-black sm:text-7xl">把书况说清楚。</h1>
        <p className="mt-5 max-w-xl leading-8 text-fog">
          品相、版本和笔记情况会进入估价依据。系统不会替代买卖双方对最终价格的确认。
        </p>
      </section>

      <form className="paper-panel p-6 sm:p-8" onSubmit={submit}>
        <label className="block text-xs font-semibold text-fog">
          选择教材
          <select
            className="field mt-1.5"
            required
            value={textbookId}
            onChange={(event) => {
              setTextbookId(event.target.value);
              setEstimate(null);
            }}
          >
            {textbooks.map((item) => (
              <option key={item.id} value={item.id}>
                {item.course_name}｜{item.title}（¥{item.new_price}）
              </option>
            ))}
          </select>
        </label>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <label className="text-xs font-semibold text-fog">
            品相
            <select
              className="field mt-1.5"
              value={condition}
              onChange={(event) => {
                setCondition(Number(event.target.value));
                setEstimate(null);
              }}
            >
              {Array.from({ length: 10 }, (_, index) => 10 - index).map((grade) => (
                <option key={grade} value={grade}>
                  {grade} 成新
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs font-semibold text-fog">
            标价
            <input
              className="field mt-1.5"
              min="1"
              required
              type="number"
              value={price}
              onChange={(event) => setPrice(Number(event.target.value))}
            />
          </label>
        </div>

        <label className="mt-4 block text-xs font-semibold text-fog">
          书况说明
          <textarea
            className="field mt-1.5 min-h-28 resize-y"
            maxLength={1000}
            placeholder="例如：第 3—5 章有少量笔记，无缺页。"
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>

        <div className="mt-4">
          <label className="block text-xs font-semibold text-fog">
            实拍图片（可选）
            <input
              accept="image/jpeg,image/png,image/webp"
              className="field mt-1.5 cursor-pointer file:mr-3 file:border-0 file:bg-ink file:px-3 file:py-1.5 file:text-xs file:text-chalk"
              onChange={pickImage}
              type="file"
            />
          </label>
          <p className="mt-1 text-[11px] text-fog">JPG、PNG 或 WebP，单张不超过 5 MB。</p>
          {imagePreview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              alt="待上传的书籍照片预览"
              className="mt-3 h-32 w-full border border-ink/20 bg-white/70 object-contain"
              src={imagePreview}
            />
          ) : null}
        </div>

        <div className="mt-5 border-y border-ink/20 py-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs text-fog">估价参考</p>
              <p className="display-title mt-1 text-3xl font-black">
                {estimate ? `¥${estimate.suggested_price.toFixed(0)}` : "尚未计算"}
              </p>
            </div>
            <button className="secondary-button" onClick={calculate} type="button">
              计算价格区间
            </button>
          </div>
          {estimate ? (
            <p className="mt-3 text-xs leading-5 text-fog">
              合理区间 ¥{estimate.low_price.toFixed(0)}—{estimate.high_price.toFixed(0)}；
              {estimate.disclaimer}
            </p>
          ) : null}
        </div>

        {error ? <p className="mt-4 border-l-4 border-brick pl-3 text-sm text-brick">{error}</p> : null}
        <button
          className="primary-button mt-5 w-full disabled:cursor-wait disabled:opacity-60"
          disabled={loading || !textbookId}
          type="submit"
        >
          {loading ? "正在发布…" : "发布到教材索引"}
        </button>
      </form>
    </main>
  );
}
