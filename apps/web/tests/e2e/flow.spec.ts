import { expect, type Page, test } from "@playwright/test";

// A valid 1x1 PNG used for the upload path. The API validates magic bytes.
const ONE_PIXEL_PNG = Buffer.from(
  "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489" +
    "0000000D49444154789C6360000000020001E221BC330000000049454E44AE426082",
  "hex",
);

test.describe.configure({ mode: "serial" });

async function loginAs(page: Page, demo: "买家" | "卖家" | "管理员") {
  await page.goto("/login");
  await page.getByRole("button", { name: new RegExp(demo) }).click();
  await page.getByRole("button", { name: "进入工作台" }).click();
  await expect(page).toHaveURL(/\/$/);
}

test("首页展示在售教材并给出合成模型估价", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /让一本书/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "走沙箱下单" }).first()).toBeVisible();

  await page.getByRole("button", { name: "生成估价依据" }).click();
  await expect(page.getByText(/synthetic-ridge-v2/)).toBeVisible();
});

test("买家登录并完成沙箱下单与支付", async ({ page }) => {
  await loginAs(page, "买家");
  await expect(page.getByText("林同学")).toBeVisible();

  await page.getByRole("button", { name: "走沙箱下单" }).first().click();
  await expect(page).toHaveURL(/\/orders$/);
  await expect(page.getByText("已支付，待交接").first()).toBeVisible();
});

test("卖家发布带实拍图片的教材", async ({ page }) => {
  await loginAs(page, "卖家");
  await page.goto("/publish");

  await page.getByLabel("标价").fill("20");
  await page
    .getByLabel("书况说明")
    .fill("E2E 发布测试：封面完好，无缺页，附赠公式卡。");
  await page.locator('input[type="file"]').setInputFiles({
    name: "cover.png",
    mimeType: "image/png",
    buffer: ONE_PIXEL_PNG,
  });
  await expect(page.getByAltText("待上传的书籍照片预览")).toBeVisible();

  await page.getByRole("button", { name: "发布到教材索引" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByText("E2E 发布测试：封面完好，无缺页，附赠公式卡。"),
  ).toBeVisible();
  await expect(page.getByAltText(/实拍图/).first()).toBeVisible();
});

test("管理员可查看运营指标，普通学生被拒绝", async ({ page }) => {
  await loginAs(page, "管理员");
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "平台脉搏" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "书籍审核" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "退款管理" })).toBeVisible();
  await expect(page.getByText("教材条目")).toBeVisible();
  await expect(page.getByText("在售书籍")).toBeVisible();
});

test("管理员可下架并恢复书籍，并通过 UI 退款", async ({ page }) => {
  await loginAs(page, "管理员");
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "书籍审核" })).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept("E2E 下架"));
  await page.getByRole("button", { name: "下架", exact: true }).first().click();
  await expect(page.getByText(/已下架《/)).toBeVisible();

  await page.getByRole("button", { name: "恢复", exact: true }).first().click();
  await expect(page.getByText(/已恢复《/)).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept("E2E 退款"));
  await page.getByRole("button", { name: "退款", exact: true }).first().click();
  await expect(page.getByText(/已退款，书籍恢复在售/)).toBeVisible();
});

test("学生访问管理页会被送回登录页", async ({ page }) => {
  await loginAs(page, "买家");
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/login$/);
});
