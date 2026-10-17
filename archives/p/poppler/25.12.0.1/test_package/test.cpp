// poppler 25.12.0.1 鸿蒙 PC 适配验证。
//
// R34：不做「只打印头文件里的版本宏」这类空壳测试——那种写法完全不触碰库代码，
// 把 lib/ 整个删掉也照样通过（CI 的 L1e 破坏性反向验证正是查这个）。
// 本文件直接调用 poppler-cpp 公共 API 做真实解析：在内存里现造一份合法 PDF
// （xref 偏移运行时计算，不写死）→ 交给 poppler 解析 → 校验页数与页面尺寸，
// 并抽取文本核对内容。这条路径会真正走到 PDF 词法分析、xref 解析、字体处理与文本抽取。
#include <poppler/cpp/poppler-document.h>
#include <poppler/cpp/poppler-page.h>
#include <poppler/cpp/poppler-version.h>

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

static int g_failed = 0;
static int g_total = 0;

static void check(bool ok, const char *what, const std::string &detail = "") {
    g_total++;
    std::printf("  [%s] %s%s%s\n", ok ? "ok" : "FAIL", what,
                detail.empty() ? "" : " — ", detail.c_str());
    if (!ok) g_failed++;
}

// 造一份最小但**合法**的单页 PDF：含 Helvetica 文本 "HarmonyOS PC"。
// xref 表里的字节偏移必须与实际内容严格一致，故边拼边记录，不硬编码。
static std::string makeMinimalPdf() {
    const std::string content = "BT /F1 24 Tf 20 100 Td (HarmonyOS PC) Tj ET\n";

    const std::vector<std::string> objs = {
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        "<< /Length " + std::to_string(content.size()) + " >>\nstream\n" + content + "endstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    };

    std::string pdf = "%PDF-1.4\n";
    std::vector<size_t> offsets;
    for (size_t i = 0; i < objs.size(); ++i) {
        offsets.push_back(pdf.size());                       // 记录本对象的字节偏移
        pdf += std::to_string(i + 1) + " 0 obj\n" + objs[i] + "\nendobj\n";
    }

    const size_t xrefPos = pdf.size();
    std::ostringstream xref;
    xref << "xref\n0 " << (objs.size() + 1) << "\n";
    xref << "0000000000 65535 f \n";
    for (size_t off : offsets) {
        char buf[32];
        std::snprintf(buf, sizeof(buf), "%010zu 00000 n \n", off);
        xref << buf;
    }
    xref << "trailer\n<< /Size " << (objs.size() + 1) << " /Root 1 0 R >>\n"
         << "startxref\n" << xrefPos << "\n%%EOF\n";
    return pdf + xref.str();
}

int main() {
    std::printf("poppler %s（编译期头 POPPLER_VERSION=%s）\n",
                poppler::version_string().c_str(), POPPLER_VERSION);

    // 头与库版本一致，否则说明链到了别的 poppler
    check(poppler::version_string() == std::string(POPPLER_VERSION), "头/库版本一致");

    const std::string pdfData = makeMinimalPdf();
    const char *path = "poppler_ohos_probe.pdf";
    {
        std::ofstream f(path, std::ios::binary);
        f.write(pdfData.data(), static_cast<std::streamsize>(pdfData.size()));
    }

    // ── 从文件解析 ─────────────────────────────────────────────────────────
    std::unique_ptr<poppler::document> doc(poppler::document::load_from_file(path));
    if (!doc) {
        check(false, "document::load_from_file 解析 PDF", "返回空指针");
        std::remove(path);
        std::printf("\n结论 FAIL：%d 项断言，%d 项失败\n", g_total, g_failed);
        return 1;
    }
    check(true, "document::load_from_file 解析 PDF",
          std::to_string(pdfData.size()) + " 字节");
    check(!doc->is_locked(), "文档未加密锁定");

    {
        char d[64];
        std::snprintf(d, sizeof(d), "pages=%d", doc->pages());
        check(doc->pages() == 1, "页数为 1", d);
    }

    // ── 取页面并校验尺寸（MediaBox 300x200）───────────────────────────────
    std::unique_ptr<poppler::page> pg(doc->create_page(0));
    if (!pg) {
        check(false, "create_page(0)", "返回空指针");
    } else {
        check(true, "create_page(0)");
        const poppler::rectf r = pg->page_rect();
        char d[96];
        std::snprintf(d, sizeof(d), "%.0fx%.0f", r.width(), r.height());
        check(r.width() == 300.0 && r.height() == 200.0, "页面尺寸 300x200", d);

        // ── 文本抽取：真正走到字体与内容流解析 ──────────────────────────
        const poppler::ustring txt = pg->text();
        const poppler::byte_array utf8 = txt.to_utf8();
        const std::string s(utf8.begin(), utf8.end());
        check(s.find("HarmonyOS") != std::string::npos,
              "抽取到页面文本 HarmonyOS", "实际抽到: \"" + s + "\"");
    }

    // ── 从内存解析同一份数据，验证另一条入口 ───────────────────────────────
    {
        poppler::byte_array data(pdfData.begin(), pdfData.end());
        std::unique_ptr<poppler::document> d2(poppler::document::load_from_data(&data));
        check(d2 && d2->pages() == 1, "document::load_from_data 解析同一份数据");
    }

    std::remove(path);
    std::printf("\n%s：%d 项断言，%d 项失败\n", g_failed ? "结论 FAIL" : "结论 PASS",
                g_total, g_failed);
    return g_failed ? 1 : 0;
}
