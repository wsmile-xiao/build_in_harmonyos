/* poppler 25.12.0.2 真实功能断言。
 *
 * 本版相对 25.12.0.1 的**唯一目的**是打开 glib 前端（ENABLE_GLIB=ON），
 * 因为 graphviz 的 poppler 插件按 `poppler-glib` 这个 pkg-config 名找它，
 * 而旧版只编了核心库（configure 报 `checking for poppler-glib... no`）。
 *
 * 所以断言的核心是**真用 glib API 打开一个 PDF 并读出页信息** ——
 * 只验 `poppler_get_version()` 非空是不够的：那个函数在核心库里就有，
 * glib 前端没编出来照样能链上（本仓反复吃过「符号在≠功能在」的亏）。
 *
 * PDF 用一个手写的最小合法文件，页数与页面尺寸都是**写死在文件里的定值**，
 * 因此可以逐项精确比对，不依赖任何外部素材。
 */
#include <poppler/glib/poppler.h>
#include <cstdio>
#include <cstring>
#include <cmath>

/* 最小合法 PDF：1 页，MediaBox 200x100。
 * 结构是手写的（trailer 直接给 Root），poppler 能容错解析。 */
static const char MINI_PDF[] =
    "%PDF-1.4\n"
    "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] >>\nendobj\n"
    "trailer\n<< /Root 1 0 R /Size 4 >>\n"
    "%%EOF\n";

#define EXPECT_PAGES  1
#define EXPECT_W    200.0
#define EXPECT_H    100.0

static int test_version(void)
{
    const char *v = poppler_get_version();
    std::printf("poppler 版本: %s\n", v ? v : "(null)");
    if (!v || !*v) { std::printf("FAIL poppler_get_version 为空\n"); return 1; }
    if (std::strncmp(v, "25.12.", 6) != 0) {
        std::printf("FAIL 版本 %s 不是 25.12.x\n", v); return 1;
    }
    return 0;
}

/* glib 前端真打开 PDF —— 这是本版本存在的理由，必须真跑通。 */
static int test_glib_frontend(void)
{
    GError *err = NULL;
    GBytes *bytes = g_bytes_new_static(MINI_PDF, sizeof(MINI_PDF) - 1);
    PopplerDocument *doc = poppler_document_new_from_bytes(bytes, NULL, &err);

    if (!doc) {
        std::printf("FAIL poppler_document_new_from_bytes 返回空: %s\n",
                    err ? err->message : "(无错误信息)");
        std::printf("     若怀疑 glib 前端根本没编进来，看 configure 摘要的 `glib wrapper`；\n"
                    "     它要求先找到 cairo，而 cairo 找不着的历史真因是 conan 的\n"
                    "     cairo-config.cmake 抢走了 find_package(Cairo)，\n"
                    "     须用生成器的 --prefer-upstream-find 让上游 FindCairo.cmake 有机会跑。\n");
        if (err) g_error_free(err);
        g_bytes_unref(bytes);
        return 1;
    }

    int n = poppler_document_get_n_pages(doc);
    if (n != EXPECT_PAGES) {
        std::printf("FAIL 页数 %d != %d\n", n, EXPECT_PAGES);
        g_object_unref(doc); g_bytes_unref(bytes); return 1;
    }

    PopplerPage *page = poppler_document_get_page(doc, 0);
    if (!page) {
        std::printf("FAIL 取不到第 1 页\n");
        g_object_unref(doc); g_bytes_unref(bytes); return 1;
    }

    double w = 0, h = 0;
    poppler_page_get_size(page, &w, &h);
    /* MediaBox 写死 200x100，解析出来必须一致（PDF 单位就是 point，无换算） */
    if (std::fabs(w - EXPECT_W) > 0.01 || std::fabs(h - EXPECT_H) > 0.01) {
        std::printf("FAIL 页面尺寸 %.2f x %.2f，期望 %.1f x %.1f\n",
                    w, h, EXPECT_W, EXPECT_H);
        g_object_unref(page); g_object_unref(doc); g_bytes_unref(bytes); return 1;
    }

    std::printf("glib 前端 OK: 解析 PDF 得 %d 页，页面 %.0f x %.0f "
                "—— ENABLE_GLIB 已生效（graphviz 的 poppler 插件正是按 poppler-glib 找它）\n",
                n, w, h);

    g_object_unref(page);
    g_object_unref(doc);
    g_bytes_unref(bytes);
    return 0;
}

/* 负例：损坏的数据必须**打不开**。
 * 只验「好文件能打开」的话，一个永远返回非空的桩实现也能通过。 */
static int test_reject_garbage(void)
{
    GError *err = NULL;
    const char junk[] = "this is definitely not a pdf file at all";
    GBytes *bytes = g_bytes_new_static(junk, sizeof(junk) - 1);
    PopplerDocument *doc = poppler_document_new_from_bytes(bytes, NULL, &err);

    if (doc) {
        std::printf("FAIL 垃圾数据竟然被当成 PDF 打开了\n");
        g_object_unref(doc); g_bytes_unref(bytes);
        if (err) g_error_free(err);
        return 1;
    }
    /* 打不开时必须给出错误信息，而不是静默返回 NULL */
    if (!err) {
        std::printf("FAIL 打不开却没设置 GError（消费方无从判断原因）\n");
        g_bytes_unref(bytes); return 1;
    }
    std::printf("负例 OK: 垃圾数据被正确拒绝（%s）\n", err->message);
    g_error_free(err);
    g_bytes_unref(bytes);
    return 0;
}

int main()
{
    if (test_version())        return 1;
    if (test_glib_frontend())  return 1;
    if (test_reject_garbage()) return 1;
    std::printf("poppler 25.12.0.2: 全部断言通过\n");
    return 0;
}
