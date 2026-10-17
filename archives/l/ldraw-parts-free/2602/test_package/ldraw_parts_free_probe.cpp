// ldraw_parts_free_probe — ldraw-parts-free 2602 消费者测试执行器
//
// 以 LDraw 消费工具视角真实使用 DFSG 自由子集（与 LeoCAD/LDView 的最小
// 功能流同构）：7 个测试用例逐例独立判定，每例输出 TEST PASS/FAIL，末尾
// TEST SUMMARY: N passed, 0 failed，任一失败进程退出码 1。
//
//   1 包内清单（32383 文件 DFSG 自由子集，textures/mklist 不携带）
//   2 内容锚点 + 被剔著名件负向（2412b/10048/10928/car/pyramid）
//   3 全树 32241 .dat 许可不变量（首个生效 "0 !LICENSE" 行精确
//     等于 CC BY 4.0 行，与 gendfsgsrc.py 同语义：被注释的历史旧
//     许可行 "0 // !LICENSE ..." 不参与判定）
//   4 引用自包含（368173 个 type-1 引用全部在库内解析成功）
//   5 LDConfig 颜色配置 + CC 许可证文本
//   6 截断/坏头/非自由许可注入负向
//   7 消费者端到端：最小 LDraw 渲染管线（解析 3001 装配体 → type-1
//     引用递归解析至子件与 p/ 图元 → 图元几何载入 → 几何颜色索引
//     全部在 LDConfig 颜色表中解析）
//
// 用法: ldraw_parts_free_probe <library-dir>

#include <dirent.h>
#include <sys/stat.h>

#include <cstdint>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace {

bool ends_with(const std::string& value, const std::string& suffix) {
    return value.size() >= suffix.size() &&
           value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

bool starts_with(const std::string& value, const std::string& prefix) {
    return value.size() >= prefix.size() &&
           value.compare(0, prefix.size(), prefix) == 0;
}

bool is_regular_file(const std::string& path) {
    struct stat info {};
    return ::stat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode);
}

bool dir_exists(const std::string& path) {
    DIR* d = ::opendir(path.c_str());
    if (d) ::closedir(d);
    return d != nullptr;
}

std::string read_file(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    return std::string((std::istreambuf_iterator<char>(in)),
                       std::istreambuf_iterator<char>());
}

bool contains(const std::string& haystack, const std::string& needle) {
    return haystack.find(needle) != std::string::npos;
}

// 去掉行尾 \r（.dat 混用 CRLF/LF，getline 只剥 \n）。
std::string rstrip_cr(const std::string& line) {
    std::string s = line;
    if (!s.empty() && s.back() == '\r') s.pop_back();
    return s;
}

// 平铺计数：dir 下扩展名匹配的常规文件数（"" 计所有文件）。
int count_files(const std::string& dir, const std::string& ext) {
    DIR* d = ::opendir(dir.c_str());
    if (!d) return -1;
    int n = 0;
    dirent* e;
    while ((e = ::readdir(d))) {
        std::string name = e->d_name;
        if (name == "." || name == "..") continue;
        if (!ends_with(name, ext)) continue;
        if (is_regular_file(dir + "/" + name)) ++n;
    }
    ::closedir(d);
    return n;
}

// 递归计数：包内文件总数。
long count_recursive(const std::string& dir) {
    long n = 0;
    DIR* d = ::opendir(dir.c_str());
    if (!d) return -1;
    dirent* e;
    while ((e = ::readdir(d))) {
        std::string name = e->d_name;
        if (name == "." || name == "..") continue;
        std::string path = dir + "/" + name;
        struct stat info {};
        if (::stat(path.c_str(), &info) != 0) continue;
        if (S_ISDIR(info.st_mode)) n += count_recursive(path);
        else if (S_ISREG(info.st_mode)) ++n;
    }
    ::closedir(d);
    return n;
}

// 递归收集 .dat 文件（完整路径, 相对库根路径），并记下相对路径集合。
void collect_dat(const std::string& dir, const std::string& rel,
                 std::vector<std::pair<std::string, std::string>>& out,
                 std::set<std::string>& relset) {
    DIR* d = ::opendir(dir.c_str());
    if (!d) return;
    dirent* e;
    while ((e = ::readdir(d))) {
        std::string name = e->d_name;
        if (name == "." || name == "..") continue;
        std::string path = dir + "/" + name;
        struct stat info {};
        if (::stat(path.c_str(), &info) != 0) continue;
        if (S_ISDIR(info.st_mode)) {
            collect_dat(path, rel + "/" + name, out, relset);
        } else if (S_ISREG(info.st_mode) && ends_with(name, ".dat")) {
            out.push_back({path, rel + "/" + name});
            relset.insert(rel + "/" + name);
        }
    }
    ::closedir(d);
}

// 归一化 LDraw 反斜杠引用为 / 分隔。
std::string slashify(const std::string& s) {
    std::string r = s;
    for (auto& c : r)
        if (c == '\\') c = '/';
    return r;
}

// 单文件校验：LDraw 格式 + 自由许可不变量；通过返回空串。
// 要求（1）首行以 "0 " 开头（2）含 "0 Name:" 行（3）第一个生效
// "0 !LICENSE" 行必须精确等于 CC BY 4.0 行。与 Debian gendfsgsrc.py
// 同语义：只认生效许可行（"0 !LICENSE" 前缀），历史注释里被注释掉的
// 旧许可行（如 "0 // !LICENSE Redistributable under CCAL version 2.0"，
// 973pxis01.dat 第 145 行实证）不参与判定。
std::string validate_dat(const std::string& path) {
    const std::string kLicense =
        "0 !LICENSE Licensed under CC BY 4.0 : see CAreadme.txt";
    std::ifstream in(path, std::ios::binary);
    std::string first;
    if (!std::getline(in, first)) return "unreadable";
    if (!starts_with(first, "0 ")) return "bad header";
    bool has_name = false;
    bool has_license = false;
    std::string line;
    while (std::getline(in, line)) {
        std::string s = rstrip_cr(line);
        if (starts_with(s, "0 Name:")) has_name = true;
        if (starts_with(s, "0 !LICENSE")) {
            if (s == kLicense) {
                has_license = true;
                break;  // 首个生效许可行即判定依据，其后为几何数据
            }
            return "non-free license line";
        }
    }
    if (!has_name) return "missing name";
    if (!has_license) return "missing CC-BY-4.0 license line";
    return "";
}

// 提取 type-1 引用文件名（第 15 个 token，\ 归一为 /）。
std::string ref_of(const std::string& line) {
    std::istringstream ss(line);
    std::string tok;
    int i = 0;
    while (ss >> tok) {
        if (i == 14) return slashify(tok);
        ++i;
    }
    return "";
}

// 提取几何行颜色索引（第 2 个 token）。
int colour_of(const std::string& line) {
    std::istringstream ss(line);
    std::string tok;
    int i = 0;
    while (ss >> tok) {
        if (i == 1) return std::atoi(tok.c_str());
        ++i;
    }
    return -1;
}

// 全树收集结果（用例 3 填充，用例 4/7 复用）。
std::vector<std::pair<std::string, std::string>> g_dats;  // (完整路径, 相对路径)
std::set<std::string> g_relset;
std::vector<std::pair<std::string, std::string>> g_refs;  // (引用者目录, 引用名)

// LDraw 引用解析（gendfsgsrc.py 同款候选集）：引用名 → 引用文件所在
// 目录 → p/ → parts/（相对库根）。
bool resolve_ref(const std::string& ownerdir, const std::string& ref,
                 std::string& out) {
    const std::string cands[4] = {ref, ownerdir + "/" + ref, "p/" + ref,
                                  "parts/" + ref};
    for (const auto& c : cands)
        if (g_relset.count(c)) {
            out = c;
            return true;
        }
    return false;
}

// ---- 测试执行器（rule12 口径：逐例独立判定 + 汇总 + 失败退出码 1）----

struct CaseResult {
    std::string name;
    int failures = 0;
};

CaseResult g_case;
std::vector<CaseResult> g_results;

void begin_case(const std::string& name) {
    g_case.name = name;
    g_case.failures = 0;
    std::cout << "== TEST CASE " << g_case.name << " ==\n";
}

void check(bool condition, const std::string& what) {
    if (!condition) {
        std::cerr << "    FAIL: " << what << "\n";
        ++g_case.failures;
    } else {
        std::cout << "    ok  - " << what << "\n";
    }
}

void end_case() {
    std::cout << "TEST " << (g_case.failures ? "FAIL" : "PASS") << ": "
              << g_case.name << "\n\n";
    g_results.push_back(g_case);
}

void case1_manifest(const std::string& lib) {
    begin_case("包内清单（32383 文件 DFSG 自由子集）");
    const char* roots[] = {"Readme.txt", "LDConfig.ldr", "LDCfgalt.ldr",
                           "LDConfig_TLG.ldr", "CAreadme.txt", "CAlicense.txt",
                           "CAlicense4.txt"};
    for (const char* f : roots)
        check(is_regular_file(lib + "/" + f), std::string("根文件在位: ") + f);
    check(!is_regular_file(lib + "/mklist.c"),
          "mklist.c 不携带（属 ldraw-mklist 二进制包）");
    check(!dir_exists(lib + "/include"), "include/ 不携带（mklist 工具头文件）");
    check(count_files(lib + "/parts", ".dat") == 21186, "parts/*.dat == 21186");
    check(count_files(lib + "/parts/s", ".dat") == 8267, "parts/s/*.dat == 8267");
    check(!dir_exists(lib + "/parts/textures"),
          "parts/textures/ 不携带（dfsg 整类剔除 135 张 PNG）");
    check(count_files(lib + "/p", ".dat") == 1741, "p/*.dat == 1741");
    check(count_files(lib + "/p/8", ".dat") == 127, "p/8/*.dat == 127");
    check(count_files(lib + "/p/48", ".dat") == 920, "p/48/*.dat == 920");
    check(count_files(lib + "/models", "") == 135, "models/ == 135 文件");
    check(count_files(lib + "/models", ".txt") == 135, "models/*.txt == 135");
    check(count_files(lib + "/models", ".dat") == 0,
          "models/*.dat == 0（样例模型被剔）");
    check(count_recursive(lib) == 32383, "包内递归总数 == 32383");
    check(is_regular_file(lib + "/../../licenses/CAlicense.txt"),
          "licenses/CAlicense.txt 在位（包级 licenses/ 布局）");
    end_case();
}

void case2_anchors(const std::string& lib) {
    begin_case("内容锚点与被剔件负向");
    // 3001.dat — 最经典零件（2x4 砖，James Jessiman 原作，CC-BY-4.0 保留）
    const std::string brick = read_file(lib + "/parts/3001.dat");
    check(contains(brick, "0 Brick  2 x  4"), "3001.dat 描述行 (Brick 2x4)");
    check(contains(brick, "0 Name: 3001.dat"), "3001.dat Name 行");
    check(contains(brick, "0 Author: James Jessiman"), "3001.dat 作者行");
    // 2-4edge.dat — 经典标准图元
    const std::string edge = read_file(lib + "/p/2-4edge.dat");
    check(contains(edge, "0 Circle 0.5"), "p/2-4edge.dat 描述行");
    check(contains(edge, "0 Name: 2-4edge.dat"), "p/2-4edge.dat Name 行");
    // p/48/1-4cyli.dat — 高分辨率图元（Name 含 48\ 前缀）
    const std::string cyli = read_file(lib + "/p/48/1-4cyli.dat");
    check(contains(cyli, "0 Name: 48\\1-4cyli.dat"), "p/48/1-4cyli.dat Name 行");
    check(contains(cyli, "0 !LDRAW_ORG 48_Primitive"),
          "p/48/1-4cyli.dat 官方 48 图元标记");
    // parts/s/3001s01.dat — 保留的子零件（Name 含 s\ 前缀）
    const std::string sub = read_file(lib + "/parts/s/3001s01.dat");
    check(contains(sub, "0 Name: s\\3001s01.dat"), "s/3001s01.dat Name 行");
    check(contains(sub, "0 !LDRAW_ORG Subpart"), "s/3001s01.dat 官方子件标记");
    // 3001p01.dat — 印刷件（CC-BY-4.0 印刷零件保留）
    const std::string print = read_file(lib + "/parts/3001p01.dat");
    check(contains(print, "0 Name: 3001p01.dat"), "3001p01.dat Name 行");
    check(contains(print, "Black Rectangles Pattern"), "3001p01.dat 印刷描述");
    // models 更新记录
    check(is_regular_file(lib + "/models/Note2602CA.txt"),
          "models/Note2602CA.txt 2602 更新记录");
    // 被剔著名件负向锚点（DFSG 剔除 CC-BY-2.0/双许可件及其依赖）
    check(!is_regular_file(lib + "/parts/2412b.dat"),
          "2412b.dat（Tile 1x2 Grille）被剔除");
    check(!is_regular_file(lib + "/parts/10048.dat"),
          "10048.dat（Minifig Hair Tousled）被剔除");
    check(!is_regular_file(lib + "/parts/10928.dat"),
          "10928.dat（Technic Gear 8 Tooth）被剔除");
    check(!is_regular_file(lib + "/models/car.dat"), "models/car.dat 被剔除");
    check(!is_regular_file(lib + "/models/pyramid.dat"),
          "models/pyramid.dat 被剔除");
    end_case();
}

void case3_license_tree(const std::string& lib) {
    begin_case("全树许可不变量（32241 .dat）");
    collect_dat(lib + "/parts", "parts", g_dats, g_relset);
    collect_dat(lib + "/p", "p", g_dats, g_relset);
    collect_dat(lib + "/models", "models", g_dats, g_relset);
    check(static_cast<long>(g_dats.size()) == 32241, ".dat 全树数量 == 32241");
    // (引用文件相对目录, 引用名)——供用例 4 按 LDraw 解析规则查库。
    std::vector<std::pair<std::string, std::string>> refs;
    int bad = 0;
    for (const auto& entry : g_dats) {
        const std::string& path = entry.first;
        const std::string& rel = entry.second;
        const std::string reason = validate_dat(path);
        if (!reason.empty()) {
            if (bad < 5)
                std::cerr << "    FAIL: " << path << ": " << reason << "\n";
            ++bad;
        }
        // 同一遍读取收集 type-1 引用，避免二次全读。
        const std::string ownerdir = rel.substr(0, rel.find_last_of('/'));
        std::ifstream in(path, std::ios::binary);
        std::string line;
        while (std::getline(in, line)) {
            if (!starts_with(line, "1 ")) continue;
            const std::string ref = ref_of(line);
            if (!ref.empty()) refs.push_back({ownerdir, ref});
        }
    }
    g_refs.swap(refs);
    check(bad == 0,
          "32241 个 .dat 全部通过格式 + 精确 CC-BY-4.0 许可行校验");
    end_case();
}

void case4_ref_closure(const std::string& lib) {
    (void)lib;
    begin_case("引用自包含（368173 type-1）");
    check(g_refs.size() == 368173, "type-1 引用总数 == 368173");
    int missing = 0;
    for (const auto& item : g_refs) {
        std::string resolved;
        if (!resolve_ref(item.first, item.second, resolved)) ++missing;
    }
    check(missing == 0, "368173 个引用全部在库内解析成功（0 缺失）");
    end_case();
}

void case5_colours_licence(const std::string& lib) {
    begin_case("颜色配置与许可证");
    const std::string config = read_file(lib + "/LDConfig.ldr");
    int colours = 0;
    {
        std::istringstream ss(config);
        std::string line;
        while (std::getline(ss, line))
            if (starts_with(line, "0 !COLOUR")) ++colours;
    }
    check(colours == 322, "LDConfig.ldr !COLOUR 条目 == 322");
    check(contains(config, "0 !LDRAW_ORG Configuration UPDATE 2026-01-03"),
          "LDConfig.ldr 2602 配置更新标记");
    check(!read_file(lib + "/LDCfgalt.ldr").empty(), "LDCfgalt.ldr 非空");
    check(!read_file(lib + "/LDConfig_TLG.ldr").empty(), "LDConfig_TLG.ldr 非空");
    check(contains(read_file(lib + "/CAlicense4.txt"),
                   "Attribution 4.0 International"),
          "CAlicense4.txt = CC BY 4.0 法律文本");
    check(contains(read_file(lib + "/CAlicense.txt"), "Attribution 2.0"),
          "CAlicense.txt = CC BY 2.0 法律文本");
    check(contains(read_file(lib + "/CAreadme.txt"),
                   "LDRAW.ORG PARTS LIBRARY AGREEMENT"),
          "CAreadme.txt 再分发协议");
    check(contains(read_file(lib + "/Readme.txt"), "OfficialCA"),
          "Readme.txt 官方 CA 库说明");
    end_case();
}

void case6_negative_injection(const std::string& lib) {
    begin_case("注入负向（截断/坏头/非自由许可）");
    const std::string neg1 = lib + "/parts/__probe_neg1__.dat";
    const std::string neg2 = lib + "/parts/__probe_neg2__.dat";
    const std::string neg3 = lib + "/parts/__probe_neg3__.dat";
    {
        std::ofstream out(neg1, std::ios::binary);
        out << "0 Broken without name\n";
    }
    {
        std::ofstream out(neg2, std::ios::binary);
        out << "1 NotLDraw header\n0 Name: y\n";
    }
    {
        // 格式完全合法，但许可行为 CCAL 2.0——free 子集探针必须拒绝。
        std::ofstream out(neg3, std::ios::binary);
        out << "0 Test\n"
            << "0 Name: __probe_neg3__.dat\n"
            << "0 !LICENSE Redistributable under CCAL version 2.0 : "
               "see CAreadme.txt\n";
    }
    check(!validate_dat(neg1).empty(), "截断 .dat（缺 Name 行）被拒");
    check(!validate_dat(neg2).empty(), "坏头 .dat（首行非 0 注释）被拒");
    check(!validate_dat(neg3).empty(), "CCAL 2.0 许可 .dat 被拒（free 不变量）");
    ::remove(neg1.c_str());
    ::remove(neg2.c_str());
    ::remove(neg3.c_str());
    check(!is_regular_file(neg1) && !is_regular_file(neg2) &&
              !is_regular_file(neg3),
          "负向样本已清理");
    end_case();
}

// ---- 用例 7：消费者端到端 —— 最小 LDraw 渲染管线 ----
// 与 LeoCAD/LDView 消费本库的最小功能流同构：载入 LDConfig 颜色表 →
// 解析装配体（3001.dat）→ type-1 引用递归解析（子件/图元/引用者目录/
// p//parts/ 候选集）→ 图元几何行（2/3/4/5 型）载入 → 几何颜色索引
// 对照 LDConfig。这不是静态清单检查，而是真实走一遍"载入模型→解析
// 引用→产出可渲染几何"的数据消费流程。

struct Mesh {
    long files = 0;
    long refs = 0;
    long lines = 0;
    long tris = 0;
    long quads = 0;
    long opt = 0;
    long unresolved = 0;
    std::set<int> used_colours;
};

std::set<int> load_colour_table(const std::string& lib) {
    std::set<int> ids;
    std::istringstream ss(read_file(lib + "/LDConfig.ldr"));
    std::string line;
    while (std::getline(ss, line)) {
        if (!starts_with(line, "0 !COLOUR")) continue;
        std::istringstream ts(line);
        std::string tok;
        int i = 0;
        while (ts >> tok) {
            // 行形: 0 !COLOUR <Name> CODE <id> VALUE <hex> EDGE <hex>
            if (tok == "CODE") {
                if (ts >> tok) ids.insert(std::atoi(tok.c_str()));
                break;
            }
            ++i;
        }
    }
    return ids;
}

void walk_part(const std::string& lib, const std::string& rel, int depth,
               std::set<std::string>& visited, Mesh& m) {
    if (depth > 64 || visited.count(rel)) return;  // 深度护栏 + 共享子件去重
    visited.insert(rel);
    std::ifstream in(lib + "/" + rel, std::ios::binary);
    if (!in) {
        ++m.unresolved;
        return;
    }
    ++m.files;
    std::string line;
    while (std::getline(in, line)) {
        const std::string s = rstrip_cr(line);
        if (s.empty()) continue;
        const char kind = s[0];
        if (kind == '1') {
            const std::string ref = ref_of(s);
            if (ref.empty()) continue;
            ++m.refs;
            const std::string ownerdir = rel.substr(0, rel.find_last_of('/'));
            std::string target;
            if (resolve_ref(ownerdir, ref, target))
                walk_part(lib, target, depth + 1, visited, m);
            else
                ++m.unresolved;
        } else if (kind == '2' || kind == '3' || kind == '4' || kind == '5') {
            const int colour = colour_of(s);
            if (colour != 16 && colour != 24)  // 16/24 = 当前色/边色元颜色
                m.used_colours.insert(colour);
            if (kind == '2') ++m.lines;
            else if (kind == '3') ++m.tris;
            else if (kind == '4') ++m.quads;
            else ++m.opt;
        }
    }
}

void case7_render_pipeline(const std::string& lib) {
    begin_case("消费者渲染管线（3001 装配体 → 图元几何）");
    const std::set<int> colour_table = load_colour_table(lib);
    check(!colour_table.empty() && colour_table.count(0) &&
              colour_table.count(15),
          "LDConfig 颜色表载入（含 Black=0 / White=15）");
    Mesh m;
    std::set<std::string> visited;
    walk_part(lib, "parts/3001.dat", 0, visited, m);
    std::cout << "    渲染管线统计: 装配图文件 " << m.files << ", type-1 引用 "
              << m.refs << ", 线段 " << m.lines << ", 三角 " << m.tris
              << ", 四边形 " << m.quads << ", 可选线 " << m.opt << "\n";
    check(m.unresolved == 0, "3001 装配体引用递归解析 0 悬空");
    check(m.files >= 3, "装配图解析到 ≥3 个文件（零件+子件+图元）");
    check(m.refs >= 4, "type-1 引用遍历 ≥4 条（子件+图元）");
    check(m.tris + m.quads > 0, "渲染几何非空（三角+四边形 > 0）");
    int unknown_colour = 0;
    for (int c : m.used_colours)
        if (!colour_table.count(c)) ++unknown_colour;
    check(unknown_colour == 0,
          "几何颜色索引全部在 LDConfig 颜色表中解析");
    end_case();
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: ldraw_parts_free_probe <library-dir>\n";
        return 2;
    }
    const std::string lib = argv[1];

    case1_manifest(lib);
    case2_anchors(lib);
    case3_license_tree(lib);
    case4_ref_closure(lib);
    case5_colours_licence(lib);
    case6_negative_injection(lib);
    case7_render_pipeline(lib);

    int passed = 0;
    int failed = 0;
    for (const auto& r : g_results)
        r.failures ? ++failed : ++passed;
    std::cout << "TEST SUMMARY: " << passed << " passed, " << failed
              << " failed\n";
    return failed ? 1 : 0;
}
