import type { Metadata } from "next";

import { SiteHeader } from "@/components/SiteHeader";

import "./globals.css";

export const metadata: Metadata = {
  title: "校园教材循环｜Campus Book Loop",
  description: "基于校园二手教材业务方案独立实现的参考工程与 AI 实验。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <SiteHeader />
        {children}
        <footer className="border-t border-ink/20 py-8">
          <div className="page-shell flex flex-col justify-between gap-3 text-xs text-fog sm:flex-row">
            <p>校园教材循环 · 独立参考实现与 AI 实验</p>
            <p>支付、用户和交易均为演示数据，不代表真实运营。</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
