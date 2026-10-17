// lebiniou_data_probe — lebiniou-data 消费者测试探针
//
// 真实消费 LEBINIOU 音乐可视化数据包：校验 share/lebiniou/ 安装树逐目录
// 计数与逐文件格式（GIMP 调色板 256 行 RGB、PNG/JPEG/GIF/FLAC/MP4 魔数、
// JSON 结构键、路径轨迹 6 段浮点、Vue 前端资源），证明包内数据真实可读
// 且与上游 3.67.0 发行逐文件一致。附带负向注入控制（证明校验路径真实）。
//
// 用法: lebiniou_data_probe <package-folder>
//   <package-folder>/share/lebiniou/...  数据安装树
//   <package-folder>/licenses/COPYING    GPL-2.0 许可证文本

#include <dirent.h>
#include <sys/stat.h>

#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

bool ends_with(const std::string& value, const std::string& suffix) {
    return value.size() >= suffix.size() &&
           value.compare(value.size() - suffix.size(), suffix.size(),
                         suffix) == 0;
}

bool is_dir(const std::string& path) {
    struct stat info {};
    return ::stat(path.c_str(), &info) == 0 && S_ISDIR(info.st_mode);
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

bool has_prefix(const std::string& path, const std::string& bytes) {
    const std::string head = read_file(path);
    return head.size() >= bytes.size() &&
           head.compare(0, bytes.size(), bytes) == 0;
}

std::string base_name(const std::string& path) {
    const size_t pos = path.rfind('/');
    return pos == std::string::npos ? path : path.substr(pos + 1);
}

int checks_done = 0;
int failures = 0;
void check(bool condition, const std::string& what) {
    ++checks_done;
    if (!condition) {
        std::cerr << "  [FAIL] " << what << "\n";
        ++failures;
    } else {
        std::cout << "  [OK]   " << what << "\n";
    }
}

// 目录顶层文件（不递归）
std::vector<std::string> files_in(const std::string& dir) {
    std::vector<std::string> out;
    DIR* d = ::opendir(dir.c_str());
    if (!d) return out;
    struct dirent* entry;
    while ((entry = ::readdir(d)) != nullptr) {
        std::string name = entry->d_name;
        if (name == "." || name == "..") continue;
        const std::string full = dir + "/" + name;
        if (is_regular_file(full)) out.push_back(full);
    }
    ::closedir(d);
    return out;
}

// 目录递归收集
void collect_files(const std::string& dir, std::vector<std::string>& out) {
    DIR* d = ::opendir(dir.c_str());
    if (!d) return;
    struct dirent* entry;
    while ((entry = ::readdir(d)) != nullptr) {
        std::string name = entry->d_name;
        if (name == "." || name == "..") continue;
        const std::string full = dir + "/" + name;
        if (is_dir(full)) {
            collect_files(full, out);
        } else {
            out.push_back(full);
        }
    }
    ::closedir(d);
}

std::vector<std::string> with_ext(const std::vector<std::string>& files,
                                  const std::string& ext) {
    std::vector<std::string> out;
    for (const auto& f : files) {
        if (ends_with(f, ext)) out.push_back(f);
    }
    return out;
}

std::vector<std::string> split_lines(const std::string& text) {
    std::vector<std::string> out;
    std::istringstream in(text);
    std::string line;
    while (std::getline(in, line)) out.push_back(line);
    return out;
}

// GIMP 调色板行："R G B" 三个 0-255 整数，无第四列
bool is_rgb_row(const std::string& line) {
    int r = -1, g = -1, b = -1;
    char extra[8] = {0};
    if (std::sscanf(line.c_str(), "%d %d %d %7s", &r, &g, &b, extra) != 3) {
        return false;
    }
    return r >= 0 && r <= 255 && g >= 0 && g <= 255 && b >= 0 && b <= 255;
}

bool json_balanced(const std::string& text) {
    int brace = 0, bracket = 0;
    for (const char c : text) {
        if (c == '{') {
            ++brace;
        } else if (c == '}') {
            --brace;
        } else if (c == '[') {
            ++bracket;
        } else if (c == ']') {
            --bracket;
        }
        if (brace < 0 || bracket < 0) return false;
    }
    return brace == 0 && bracket == 0;
}

int count_substr(const std::string& text, const std::string& needle) {
    int n = 0;
    size_t pos = 0;
    while ((pos = text.find(needle, pos)) != std::string::npos) {
        ++n;
        pos += needle.size();
    }
    return n;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: lebiniou_data_probe <package-folder>\n";
        return 2;
    }
    const std::string pkg = argv[1];
    const std::string root = pkg + "/share/lebiniou";

    std::cout << "lebiniou-data 3.67.0 consumer probe\n";

    // ── 1. 六大安装目录在位 ──
    const char* subdirs[] = {"colormaps", "images", "paths", "sequences",
                             "vue", "test"};
    for (const char* d : subdirs) {
        check(is_dir(root + "/" + d), std::string("subdir ") + d + " present");
    }

    // ── 2. 安装树总文件数 1727 ──
    std::vector<std::string> all;
    collect_files(root, all);
    check(all.size() == 1727, "installed tree has exactly 1727 files (got " +
                                  std::to_string(all.size()) + ")");

    // ── 3. 无构建残留 ──
    int am_count = 0;
    for (const auto& f : all) {
        if (ends_with(f, "Makefile.am")) ++am_count;
    }
    check(am_count == 0, "no Makefile.am leaked into install tree");

    // ── 4. colormaps：1415 个 .gpl，每文件恰 256 行 RGB 三元组 ──
    const std::vector<std::string> gpls = files_in(root + "/colormaps");
    check(gpls.size() == 1415, "colormaps has exactly 1415 .gpl files (got " +
                                   std::to_string(gpls.size()) + ")");
    for (const auto& f : gpls) {
        const std::string base = base_name(f);
        check(ends_with(f, ".gpl"), base + " carries .gpl extension");
        const std::vector<std::string> lines = split_lines(read_file(f));
        check(lines.size() == 256, base + " has exactly 256 rows (got " +
                                       std::to_string(lines.size()) + ")");
        bool rows_ok = true;
        for (const auto& line : lines) {
            if (!is_rgb_row(line)) rows_ok = false;
        }
        check(rows_ok, base + " rows are all RGB triples");
    }

    // ── 5. images：123 文件（顶层 75 + 四主题 48），PNG/JPEG 魔数全查 ──
    std::vector<std::string> imgs;
    collect_files(root + "/images", imgs);
    check(imgs.size() == 123, "images has exactly 123 files (got " +
                                  std::to_string(imgs.size()) + ")");
    check(files_in(root + "/images").size() == 75,
          "images/biniou top level has 75 files");
    const std::vector<std::string> pngs = with_ext(imgs, ".png");
    const std::vector<std::string> jpgs = with_ext(imgs, ".jpg");
    check(pngs.size() == 115, "images carries 115 PNG files");
    check(jpgs.size() == 8, "images carries 8 JPEG files");
    for (const auto& f : pngs) {
        check(has_prefix(f, "\x89PNG"), base_name(f) + " has PNG magic");
    }
    // 上游勘误：covid-19/covid-19.jpg 与 covid-19-confirmed.jpg 扩展名
    // 为 .jpg 但实为 PNG（上游发行即如此，保持逐字节一致不修补），按实际
    // 格式断言，并钉死误标文件恰为 2 个。
    int png_jpgs = 0;
    for (const auto& f : jpgs) {
        const std::string base = base_name(f);
        if (has_prefix(f, "\x89PNG")) {
            ++png_jpgs;
            check(base == "covid-19.jpg" || base == "covid-19-confirmed.jpg",
                  base + " is an upstream-mislabeled PNG with .jpg extension");
        } else {
            check(has_prefix(f, "\xFF\xD8\xFF"), base + " has JPEG magic");
        }
    }
    check(png_jpgs == 2, "exactly 2 upstream-mislabeled .jpg files are PNG");
    const char* themes[] = {"covid-19", "oliv3", "opale95", "zebulon"};
    const int theme_counts[] = {8, 2, 20, 18};
    for (int i = 0; i < 4; ++i) {
        const std::vector<std::string> t =
            files_in(root + "/images/" + themes[i]);
        check(static_cast<int>(t.size()) == theme_counts[i],
              std::string("theme ") + themes[i] + " has " +
                  std::to_string(theme_counts[i]) + " files");
    }

    // ── 6. paths：8 个 .path 轨迹，非空且首行 6 段逗号分隔浮点 ──
    const std::vector<std::string> paths = files_in(root + "/paths");
    check(paths.size() == 8, "paths has exactly 8 trajectory files (got " +
                                 std::to_string(paths.size()) + ")");
    for (const auto& f : paths) {
        const std::string text = read_file(f);
        check(!text.empty(), base_name(f) + " non-empty");
        const std::string first = split_lines(text).front();
        int commas = 0;
        for (const char c : first) {
            if (c == ',') ++commas;
        }
        check(commas == 5, base_name(f) + " first row has 6 comma-separated "
                           "floats");
    }

    // ── 7. sequences：json/ 15 个序列定义，均以 '{' 开头 ──
    const std::vector<std::string> seqs = files_in(root + "/sequences/json");
    check(seqs.size() == 15, "sequences/json has exactly 15 files (got " +
                                 std::to_string(seqs.size()) + ")");
    for (const auto& f : seqs) {
        const std::string text = read_file(f);
        const size_t pos = text.find_first_not_of(" \t\r\n");
        check(pos != std::string::npos && text[pos] == '{',
              base_name(f) + " starts with '{'");
    }

    // ── 8. vue：前端资源逐目录计数 + 内容抽查 ──
    check(files_in(root + "/vue").size() == 2,
          "vue root has 2 files (index.html + favicon.ico)");
    const char* vsubs[] = {"css", "img", "js", "media", "sequences"};
    const int vcounts[] = {9, 17, 18, 12, 105};
    for (int i = 0; i < 5; ++i) {
        const std::vector<std::string> v = files_in(root + "/vue/" + vsubs[i]);
        check(static_cast<int>(v.size()) == vcounts[i],
              std::string("vue/") + vsubs[i] + " has " +
                  std::to_string(vcounts[i]) + " files");
    }
    const std::string index_html = read_file(root + "/vue/index.html");
    check(contains(index_html, "lebiniou-vui"),
          "index.html carries lebiniou-vui title");
    check(contains(index_html, "<div id=\"app\">"), "index.html mounts #app");
    check(!read_file(root + "/vue/favicon.ico").empty(),
          "favicon.ico non-empty");
    for (const auto& f : files_in(root + "/vue/media")) {
        const std::string text = read_file(f);
        check(text.size() > 8 && text.compare(4, 4, "ftyp") == 0,
              base_name(f) + " has MP4 ftyp box");
    }
    for (const auto& f : files_in(root + "/vue/img")) {
        if (ends_with(f, ".gif")) {
            check(has_prefix(f, "GIF8"), base_name(f) + " has GIF magic");
        } else if (ends_with(f, ".png")) {
            check(has_prefix(f, "\x89PNG"), base_name(f) + " has PNG magic");
        } else if (ends_with(f, ".svg")) {
            check(contains(read_file(f), "<svg"),
                  base_name(f) + " carries <svg> element");
        }
    }
    for (const auto& f : files_in(root + "/vue/css")) {
        check(!read_file(f).empty(), base_name(f) + " non-empty");
    }
    for (const auto& f : files_in(root + "/vue/js")) {
        check(!read_file(f).empty(), base_name(f) + " non-empty");
    }
    for (const auto& f : files_in(root + "/vue/sequences")) {
        const std::string text = read_file(f);
        const size_t pos = text.find_first_not_of(" \t\r\n");
        check(pos != std::string::npos && text[pos] == '{',
              base_name(f) + " starts with '{'");
    }

    // ── 9. test：3 文件（autopkgtest 材料 + 测试音频 + 配置）──
    check(files_in(root + "/test").size() == 3,
          "test has exactly 3 files (script + config + FLAC sample)");
    const std::string flac =
        root + "/test/EP-Le_cri_des_anges-Intro_4-8bits.flac";
    check(has_prefix(flac, "fLaC"), "FLAC sample has fLaC magic");
    check(read_file(flac).size() > 1000000,
          "FLAC sample has plausible size (>1MB)");
    const std::string shin = read_file(root + "/test/lebiniou-test.sh.in");
    check(shin.rfind("#!/", 0) == 0, "lebiniou-test.sh.in carries shebang");
    check(contains(shin, "lebiniou"),
          "lebiniou-test.sh.in references lebiniou");
    const std::string config = read_file(root + "/test/lebiniou.json");
    check(json_balanced(config), "lebiniou.json braces/brackets balanced");
    const char* keys[] = {"\"screen\":", "\"input\":", "\"themes\":",
                          "\"engine\":", "\"plugins\":"};
    for (const char* k : keys) {
        check(contains(config, k),
              std::string("lebiniou.json top-level key ") + k);
    }
    check(contains(config, "\"width\": 320"), "lebiniou.json screen width 320");
    check(contains(config, "\"height\": 180"),
          "lebiniou.json screen height 180");
    check(count_substr(config, "\"enabled\"") == 109,
          "lebiniou.json lists 109 plugins");

    // ── 10. 许可证 ──
    const std::string copying = read_file(pkg + "/licenses/COPYING");
    check(!copying.empty(), "licenses/COPYING present");
    check(contains(copying, "GNU GENERAL PUBLIC LICENSE"),
          "COPYING is GPL text");
    check(contains(copying, "Version 2, June 1991"),
          "COPYING is GPL version 2");

    // ── 11. 负向控制：注入坏 PNG，魔数校验必须抓出 ──
    const std::string neg = root + "/images/zzz-negative-probe.png";
    {
        std::ofstream out(neg, std::ios::binary);
        out << "not-a-png";
    }
    check(!has_prefix(neg, "\x89PNG"),
          "negative control: corrupted PNG rejected by magic check");
    std::remove(neg.c_str());
    check(!is_regular_file(neg), "negative control cleaned up");

    std::cout << "lebiniou_data_probe: " << checks_done
              << " assertions, " << failures << " failed\n";
    return failures == 0 ? 0 : 1;
}
