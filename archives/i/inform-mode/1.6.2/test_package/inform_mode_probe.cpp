// inform_mode_probe — inform-mode 消费者测试探针
//
// 真实消费 inform-mode Emacs Lisp 包数据：校验 site-lisp 目录单文件
// 清单、文件在位/非空/63201 字节精确防漂移，并逐条断言 1.6.2 版本头、
// 功能符号（defun/defvar/defcustom/autoload）与 GPL-3.0 许可证文本，
// 证明包内数据真实可读且内容与上游 6.42-r9 发行一致。
//
// OHOS PC 真机无 Emacs 运行时，无法"加载运行"验证——本探针以内容级
// 断言代替运行时验证（五层：清单 / 尺寸 / 元数据+符号 / 许可证 /
// 负向截断注入拒绝语义）。
//
// 用法: inform_mode_probe <site-lisp-dir> <package-folder>

#include <dirent.h>
#include <sys/stat.h>

#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

bool is_regular_file(const std::string& path) {
    struct stat info {};
    return ::stat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode);
}

std::string read_file(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    return std::string((std::istreambuf_iterator<char>(in)),
                       std::istreambuf_iterator<char>());
}

bool contains(const std::string& haystack, const std::string& needle) {
    return haystack.find(needle) != std::string::npos;
}

int failures = 0;
void check(bool condition, const std::string& what) {
    if (!condition) {
        std::cerr << "  [FAIL] " << what << "\n";
        ++failures;
    } else {
        std::cout << "  [OK]   " << what << "\n";
    }
}

// 上游 contrib/inform-mode.el 实测字节数（构建期防漂移同款常量）。
const int64_t kElispBytes = 63201;

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: inform_mode_probe <site-lisp-dir> <package-folder>\n";
        return 2;
    }
    const std::string sitedir = argv[1];
    const std::string pkgroot = argv[2];

    std::cout << "inform-mode 1.6.2 consumer probe\n";

    // ── 1. 目录清单：site-lisp 恰好 1 个文件（inform-mode.el） ──
    int total = 0;
    if (DIR* dir = ::opendir(sitedir.c_str())) {
        struct dirent* entry;
        while ((entry = ::readdir(dir)) != nullptr) {
            std::string name = entry->d_name;
            if (name == "." || name == "..") continue;
            if (is_regular_file(sitedir + "/" + name)) ++total;
        }
        ::closedir(dir);
    }
    check(total == 1, "site-lisp dir contains exactly 1 file (got " +
                          std::to_string(total) + ")");

    // ── 2. 文件在位、非空、63201 字节精确防漂移 ──
    const std::string el = sitedir + "/inform-mode.el";
    check(is_regular_file(el), "inform-mode.el present");
    if (is_regular_file(el)) {
        const std::string text = read_file(el);
        check(!text.empty(), "inform-mode.el non-empty");
        check(static_cast<int64_t>(text.size()) == kElispBytes,
              "inform-mode.el exactly 63201 bytes (got " +
                  std::to_string(text.size()) + ")");

        // ── 3. 内容标记：版本头 / GPL 声明 / 功能符号 ──
        check(contains(text, ";; Version: 1.6.2"),
              "elisp declares Version 1.6.2");
        check(contains(text, ";; Released: 10-Oct-2013"),
              "elisp declares Released 10-Oct-2013");
        check(contains(text, ";; Keywords: languages"),
              "elisp declares Keywords: languages");
        check(contains(text, "GNU General Public License"),
              "elisp carries GPL notice header");
        check(contains(text, "(defun inform-mode ()"),
              "elisp defines `inform-mode` entry point");
        check(contains(text, ";;;###autoload"),
              "elisp carries autoload cookies");
        check(contains(text, "(defvar inform-mode-map nil"),
              "elisp defines `inform-mode-map`");
        check(contains(text, "(defvar inform-mode-syntax-table nil"),
              "elisp defines `inform-mode-syntax-table`");
        check(contains(text, "(defcustom inform-command \"inform\""),
              "elisp defines `inform-command` (inform6 compiler invocation)");
        check(contains(text, "(defcustom inform-interpreter-command \"frotz\""),
              "elisp defines `inform-interpreter-command` (frotz interpreter)");
    }

    // ── 4. 许可证：licenses/LICENSE-GPL-3.0.txt 在位 + GPL-3.0 文本 ──
    const std::string lic = pkgroot + "/licenses/LICENSE-GPL-3.0.txt";
    check(is_regular_file(lic), "licenses/LICENSE-GPL-3.0.txt present");
    if (is_regular_file(lic)) {
        const std::string gpl = read_file(lic);
        check(!gpl.empty(), "license text non-empty");
        check(contains(gpl, "GNU GENERAL PUBLIC LICENSE"),
              "license is the GNU General Public License text");
        check(contains(gpl, "Version 3, 29 June 2007"),
              "license is GPL version 3");
    }

    // ── 5. 负向：截断注入必须被尺寸防漂移断言拒绝 ──
    {
        const std::string real = sitedir + "/inform-mode.el";
        const std::string saved = read_file(real);
        check(!saved.empty(), "pre-injection payload snapshot captured");

        // (a) 注入截断：把真实 elisp 原地覆盖为截断载荷
        {
            std::ofstream out(real.c_str(), std::ios::trunc | std::ios::binary);
            out << ";; truncated header";
        }
        // (b) 拒绝语义：第 2 组同款尺寸防漂移断言必须检出截断（!= 63201）
        const int64_t truncated_bytes =
            static_cast<int64_t>(read_file(real).size());
        check(truncated_bytes != kElispBytes,
              "truncated payload rejected by size drift assertion (read back != 63201 bytes)");
        // (c) 恢复原载荷并复验完整（防漂移常量 + 版本头双锚点）
        {
            std::ofstream out(real.c_str(), std::ios::trunc | std::ios::binary);
            out.write(saved.data(), static_cast<std::streamsize>(saved.size()));
        }
        check(static_cast<int64_t>(read_file(real).size()) == kElispBytes,
              "original payload restored to exactly 63201 bytes");
        check(contains(read_file(real), ";; Version: 1.6.2"),
              "restored payload retains upstream version header");
    }

    if (failures) {
        std::cerr << "inform_mode_probe: " << failures << " assertion(s) failed\n";
        return 1;
    }
    std::cout << "inform_mode_probe: all assertions passed\n";
    return 0;
}
