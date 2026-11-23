"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, storeSession } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("student@campus.local");
  const [password, setPassword] = useState("DemoPass123!");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const session =
        mode === "login"
          ? await api.login(email, password)
          : await api.register(email, displayName, password);
      storeSession(session);
      router.push("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "登录失败。");
    } finally {
      setLoading(false);
    }
  };

  const fillDemoAccount = (type: "student" | "seller" | "admin") => {
    if (type === "admin") {
      setEmail("admin@campus.local");
      setPassword("AdminPass123!");
    } else if (type === "seller") {
      setEmail("seller@campus.local");
      setPassword("DemoPass123!");
    } else {
      setEmail("student@campus.local");
      setPassword("DemoPass123!");
    }
  };

  return (
    <main className="page-shell grid min-h-[calc(100vh-180px)] gap-10 py-12 lg:grid-cols-[1fr_480px] lg:items-center">
      <section>
        <p className="eyebrow">演示账号</p>
        <h1 className="display-title mt-4 max-w-3xl text-5xl font-black leading-tight sm:text-7xl">
          登录后，
          <br />
          走完一次交接。
        </h1>
        <p className="mt-6 max-w-xl leading-8 text-fog">
          买家、卖家和管理员使用不同的演示身份。所有数据均可重建，支付环节只模拟状态变化。
        </p>
        <div className="mt-8 grid max-w-xl gap-3 sm:grid-cols-3">
          {[
            ["student", "买家", "student@campus.local"],
            ["seller", "卖家", "seller@campus.local"],
            ["admin", "管理员", "admin@campus.local"],
          ].map(([key, label, account]) => (
            <button
              className="paper-panel px-4 py-4 text-left transition hover:-translate-y-1"
              key={key}
              onClick={() => fillDemoAccount(key as "student" | "seller" | "admin")}
              type="button"
            >
              <span className="block text-sm font-bold">{label}</span>
              <span className="mt-2 block break-all text-[10px] text-fog">{account}</span>
            </button>
          ))}
        </div>
        <p className="mt-4 text-xs text-fog">
          学生与卖家密码：DemoPass123!　管理员密码：AdminPass123!
        </p>
      </section>

      <section className="paper-panel p-6 sm:p-8">
        <div className="flex border-b border-ink/20">
          <button
            className={`px-5 py-3 text-sm font-bold ${
              mode === "login" ? "border-b-2 border-brick text-brick" : "text-fog"
            }`}
            onClick={() => setMode("login")}
            type="button"
          >
            登录
          </button>
          <button
            className={`px-5 py-3 text-sm font-bold ${
              mode === "register" ? "border-b-2 border-brick text-brick" : "text-fog"
            }`}
            onClick={() => setMode("register")}
            type="button"
          >
            新建演示账号
          </button>
        </div>
        <form className="mt-6 space-y-4" onSubmit={submit}>
          {mode === "register" ? (
            <label className="block text-xs font-semibold text-fog">
              显示名称
              <input
                className="field mt-1.5"
                required
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            </label>
          ) : null}
          <label className="block text-xs font-semibold text-fog">
            邮箱
            <input
              className="field mt-1.5"
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="block text-xs font-semibold text-fog">
            密码
            <input
              className="field mt-1.5"
              minLength={8}
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error ? <p className="border-l-4 border-brick pl-3 text-sm text-brick">{error}</p> : null}
          <button
            className="primary-button w-full disabled:cursor-wait disabled:opacity-60"
            disabled={loading}
            type="submit"
          >
            {loading ? "正在进入…" : mode === "login" ? "进入工作台" : "创建并登录"}
          </button>
        </form>
        <p className="mt-5 text-xs leading-6 text-fog">
          继续即表示你了解本项目使用虚构账号和演示数据。
          <Link className="ml-1 underline" href="/">
            先返回首页
          </Link>
        </p>
      </section>
    </main>
  );
}
