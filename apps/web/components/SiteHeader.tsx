"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { clearSession, getStoredUser } from "@/lib/api";
import type { User } from "@/lib/types";

export function SiteHeader() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const update = () => setUser(getStoredUser());
    update();
    window.addEventListener("cbl-session", update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener("cbl-session", update);
      window.removeEventListener("storage", update);
    };
  }, []);

  const logout = () => {
    clearSession();
    setUser(null);
  };

  return (
    <header className="border-b border-ink/20 bg-paper/90 backdrop-blur">
      <div className="page-shell flex min-h-20 items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-3" aria-label="返回首页">
          <span className="grid h-10 w-9 place-items-center border-2 border-ink bg-marigold font-display text-lg font-black">
            书
          </span>
          <span>
            <span className="block font-display text-lg font-bold leading-none">
              校园教材循环
            </span>
            <span className="mt-1 block text-[10px] font-semibold tracking-[0.16em] text-fog">
              CAMPUS BOOK LOOP
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm font-medium md:flex" aria-label="主导航">
          <Link className="hover:text-brick" href="/#catalog">
            找教材
          </Link>
          <Link className="hover:text-brick" href="/publish">
            发布旧书
          </Link>
          <Link className="hover:text-brick" href="/orders">
            我的订单
          </Link>
          {user?.role === "admin" ? (
            <Link className="hover:text-brick" href="/admin">
              运营台
            </Link>
          ) : null}
        </nav>

        <div className="flex items-center gap-3">
          {user ? (
            <>
              <span className="hidden text-sm text-fog sm:inline">{user.display_name}</span>
              <button className="secondary-button min-h-9 px-3 py-1.5" onClick={logout} type="button">
                退出
              </button>
            </>
          ) : (
            <Link className="primary-button min-h-9 px-4 py-1.5" href="/login">
              登录体验
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
