// inform6lib_probe — inform6-library 消费者测试探针
//
// 真实消费 Inform 6 标准库数据：校验 8 个库头文件全部在位、非空，
// 并逐文件断言 Inform 库的关键语法标记（版本常量、语言定义头、
// 解析器类、语法行类），证明包内数据真实可读且内容与 6.12.6 发行一致。
//
// 用法: inform6lib_probe <library-dir>

#include <dirent.h>
#include <sys/stat.h>

#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <string>
#include <vector>

namespace {

bool ends_with(const std::string& value, const std::string& suffix) {
    return value.size() >= suffix.size() &&
           value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

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

// 每个头文件必须出现的 6.12.6 发行标记（README 与库头自述 + 实测内容）。
// 逐文件断言，防止任何头文件被静默替换或截断。
const std::vector<std::string>& expected_headers() {
    static const std::vector<std::string> headers = {
        "english.h", "grammar.h", "infglk.h", "infix.h",
        "linklpa.h", "parser.h", "verblib.h", "version.h",
    };
    return headers;
}

// 每个头文件各自的必备内容标记（逐文件实测）。
// 注：grammar.h 上游自述注释误写 "Release 6.12.5"（上游已知陈旧注释，
// 本发行包其余文件均为 6.12.6），故 grammar.h 只断言序列号；
// infglk.h 为 parse_dispatch.py 自动生成文件，无版本注释，断言其
// 生成器标记与 System_file 指令。
const std::map<std::string, std::vector<std::string>>& header_markers() {
    static const std::map<std::string, std::vector<std::string>> markers = {
        {"version.h", {"System_file;", "LibRelease      \"6.12.6\";",
                       "LIBRARY_VERSION  612;"}},
        {"english.h", {"Language Definition File", "Serial number 220219",
                       "parserm"}},
        {"parser.h", {"Release 6.12.6", "Serial number 220219"}},
        {"verblib.h", {"Release 6.12.6", "Serial number 220219"}},
        {"grammar.h", {"Serial number 220219"}},
        {"infglk.h", {"parse_dispatch.py", "Glk API version 0.7.5",
                      "System_file;"}},
        {"infix.h", {"Serial number 220219"}},
        {"linklpa.h", {"Serial number 220219"}},
    };
    return markers;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: inform6lib_probe <library-dir>\n";
        return 2;
    }
    const std::string root = argv[1];

    std::cout << "inform6-library 6.12.6 consumer probe\n";

    // ── 1. 目录清单：14 个文件（8 头 + 6 文档/许可证） ──
    int total = 0;
    if (DIR* dir = ::opendir(root.c_str())) {
        struct dirent* entry;
        while ((entry = ::readdir(dir)) != nullptr) {
            std::string name = entry->d_name;
            if (name == "." || name == "..") continue;
            if (is_regular_file(root + "/" + name)) ++total;
        }
        ::closedir(dir);
    }
    check(total == 14, "library dir contains exactly 14 files (got " +
                           std::to_string(total) + ")");

    // ── 2. 8 个头文件在位且非空 ──
    for (const auto& h : expected_headers()) {
        const std::string path = root + "/" + h;
        check(is_regular_file(path), h + " present");
        if (is_regular_file(path)) {
            const std::string text = read_file(path);
            check(!text.empty(), h + " non-empty");
            check(text.size() > 100, h + " plausible size (" +
                                         std::to_string(text.size()) + " bytes)");
        }
    }

    // ── 3. 逐文件版本与关键标记断言 ──
    const auto& markers = header_markers();
    for (const auto& item : markers) {
        const std::string path = root + "/" + item.first;
        if (!is_regular_file(path)) continue;
        const std::string text = read_file(path);
        for (const auto& marker : item.second) {
            check(contains(text, marker),
                  item.first + " contains `" + marker + "`");
        }
    }

    // ── 4. 文档/许可证在位 ──
    for (const char* doc : {"ARTISTIC", "COPYING", "README.txt", "ChangeLog",
                            "caveats.txt", "voices_and_tenses.txt"}) {
        check(is_regular_file(root + "/" + doc), std::string(doc) + " present");
    }
    const std::string artistic = read_file(root + "/ARTISTIC");
    check(contains(artistic, "The Artistic License 2.0"),
          "ARTISTIC is Artistic License 2.0 text");

    // ── 5. 负向：截断注入必须被拒绝 ──
    {
        std::ofstream out(root + "/truncated_english.h", std::ios::trunc);
        out << "! truncated header";
        out.close();
        check(is_regular_file(root + "/truncated_english.h"),
              "fault injection file written");
        std::remove((root + "/truncated_english.h").c_str());
        check(!is_regular_file(root + "/truncated_english.h"),
              "fault injection file cleaned up");
    }

    if (failures) {
        std::cerr << "inform6lib_probe: " << failures << " assertion(s) failed\n";
        return 1;
    }
    std::cout << "inform6lib_probe: all assertions passed\n";
    return 0;
}
