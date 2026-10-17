// ldraw_parts_probe — ldraw-parts 2602 消费者测试探针
//
// 真实消费 LDraw 零件库数据：校验 35723 文件全库清单（parts/subparts/
// textures/primitives/models/根文件），对全树 35444 个 .dat 逐个校验
// LDraw 文件格式（首行 "0 " 注释行 + "0 Name:" 文件名行），并断言
// 代表性内容锚点、LDConfig 颜色配置与 CC 许可证双文本，附截断/坏头
// 注入负向用例——证明包内数据真实可读且内容与 2602 发行一致。
//
// 用法: ldraw_parts_probe <library-dir>

#include <dirent.h>
#include <sys/stat.h>

#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
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

std::string read_file(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    return std::string((std::istreambuf_iterator<char>(in)),
                       std::istreambuf_iterator<char>());
}

bool contains(const std::string& haystack, const std::string& needle) {
    return haystack.find(needle) != std::string::npos;
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

// 递归计数：全库文件总数。
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

// 递归收集 .dat 文件路径。
void collect_dat(const std::string& dir, std::vector<std::string>& out) {
    DIR* d = ::opendir(dir.c_str());
    if (!d) return;
    dirent* e;
    while ((e = ::readdir(d))) {
        std::string name = e->d_name;
        if (name == "." || name == "..") continue;
        std::string path = dir + "/" + name;
        struct stat info {};
        if (::stat(path.c_str(), &info) != 0) continue;
        if (S_ISDIR(info.st_mode)) collect_dat(path, out);
        else if (S_ISREG(info.st_mode) && ends_with(name, ".dat"))
            out.push_back(path);
    }
    ::closedir(d);
}

// 单文件 LDraw 格式校验：首行以 "0 " 开头且含 "0 Name:" 行；
// 通过返回空串，否则返回失败原因。
std::string validate_dat(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    std::string first;
    if (!std::getline(in, first)) return "unreadable";
    if (!starts_with(first, "0 ")) return "bad header";
    bool has_name = false;
    std::string line;
    while (std::getline(in, line)) {
        if (starts_with(line, "0 Name:")) {
            has_name = true;
            break;
        }
    }
    return has_name ? "" : "missing name";
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

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: ldraw_parts_probe <library-dir>\n";
        return 2;
    }
    const std::string lib = argv[1];

    std::cout << "== [1/5] 全库清单 (35723 文件) ==\n";
    const char* roots[] = {"Readme.txt", "LDConfig.ldr", "LDCfgalt.ldr",
                           "LDConfig_TLG.ldr", "CAreadme.txt", "CAlicense.txt",
                           "CAlicense4.txt"};
    for (const char* f : roots)
        check(is_regular_file(lib + "/" + f), std::string("根文件在位: ") + f);
    check(count_files(lib + "/parts", ".dat") == 23839, "parts/*.dat == 23839");
    check(count_files(lib + "/parts/s", ".dat") == 8813, "parts/s/*.dat == 8813");
    check(count_files(lib + "/parts/textures", ".png") == 135,
          "parts/textures/*.png == 135");
    check(count_files(lib + "/p", ".dat") == 1743, "p/*.dat == 1743");
    check(count_files(lib + "/p/8", ".dat") == 127, "p/8/*.dat == 127");
    check(count_files(lib + "/p/48", ".dat") == 920, "p/48/*.dat == 920");
    check(count_files(lib + "/models", "") == 139, "models/ == 139 文件");
    check(count_files(lib + "/models", ".txt") == 135, "models/*.txt == 135");
    check(count_recursive(lib) == 35723, "全库递归总数 == 35723");

    std::cout << "== [2/5] 代表性内容锚点 ==\n";
    // 3001.dat — 最经典零件（2x4 砖，创始人 James Jessiman 原作）
    const std::string brick = read_file(lib + "/parts/3001.dat");
    check(contains(brick, "0 Brick  2 x  4"), "3001.dat 描述行 (Brick 2x4)");
    check(contains(brick, "0 Name: 3001.dat"), "3001.dat Name 行");
    check(contains(brick, "0 Author: James Jessiman"), "3001.dat 作者行");
    // 2-4edge.dat — 经典标准图元
    const std::string edge = read_file(lib + "/p/2-4edge.dat");
    check(contains(edge, "0 Circle 0.5"), "p/2-4edge.dat 描述行");
    check(contains(edge, "0 Name: 2-4edge.dat"), "p/2-4edge.dat Name 行");
    // p/48/1-4cyli.dat — 高分辨率图元（Name 含 48\\ 前缀）
    const std::string cyli = read_file(lib + "/p/48/1-4cyli.dat");
    check(contains(cyli, "0 Name: 48\\1-4cyli.dat"), "p/48/1-4cyli.dat Name 行");
    check(contains(cyli, "0 !LDRAW_ORG 48_Primitive"),
          "p/48/1-4cyli.dat 官方 48 图元标记");
    // parts/s/003238s1.dat — 子零件（Name 含 s\\ 前缀）
    const std::string sub = read_file(lib + "/parts/s/003238s1.dat");
    check(contains(sub, "0 Name: s\\003238s1.dat"), "s/003238s1.dat Name 行");
    check(contains(sub, "0 !LDRAW_ORG Subpart"), "s/003238s1.dat 官方子件标记");
    // 3001p01.dat — 印刷件（证明完整库含印刷零件）
    const std::string print = read_file(lib + "/parts/3001p01.dat");
    check(contains(print, "0 Name: 3001p01.dat"), "3001p01.dat Name 行");
    check(contains(print, "Black Rectangles Pattern"), "3001p01.dat 印刷描述");
    // models 样例模型 + 2602 更新记录
    check(is_regular_file(lib + "/models/car.dat"), "models/car.dat 样例模型");
    check(is_regular_file(lib + "/models/pyramid.dat"),
          "models/pyramid.dat 样例模型");
    check(is_regular_file(lib + "/models/Note2602CA.txt"),
          "models/Note2602CA.txt 2602 更新记录");

    std::cout << "== [3/5] 全树 .dat 格式校验 (35444 文件) ==\n";
    std::vector<std::string> dats;
    collect_dat(lib + "/parts", dats);
    collect_dat(lib + "/p", dats);
    collect_dat(lib + "/models", dats);  // car.dat / pyramid.dat
    check(static_cast<long>(dats.size()) == 35444, ".dat 全树数量 == 35444");
    int bad = 0;
    for (const auto& path : dats)
        if (!validate_dat(path).empty()) ++bad;
    check(bad == 0, "35444 个 .dat 全部通过格式校验（首行 0 注释 + Name 行）");
    // 纹理 PNG 魔数
    int bad_png = 0;
    {
        DIR* d = ::opendir((lib + "/parts/textures").c_str());
        dirent* e;
        while (d && (e = ::readdir(d))) {
            std::string name = e->d_name;
            if (!ends_with(name, ".png")) continue;
            std::string path = lib + "/parts/textures/" + name;
            if (!is_regular_file(path)) continue;
            std::ifstream in(path, std::ios::binary);
            char magic[4] = {0, 0, 0, 0};
            in.read(magic, 4);
            if (!(magic[0] == (char)0x89 && magic[1] == 'P' &&
                  magic[2] == 'N' && magic[3] == 'G'))
                ++bad_png;
        }
        if (d) ::closedir(d);
    }
    check(bad_png == 0, "135 个纹理 PNG 魔数全部正确");

    std::cout << "== [4/5] 颜色配置与许可证 ==\n";
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

    std::cout << "== [5/5] 截断/坏头注入负向 ==\n";
    const std::string neg1 = lib + "/parts/__probe_neg1__.dat";
    const std::string neg2 = lib + "/parts/__probe_neg2__.dat";
    {
        std::ofstream out(neg1, std::ios::binary);
        out << "0 Broken without name\n";
    }
    {
        std::ofstream out(neg2, std::ios::binary);
        out << "1 NotLDraw header\n0 Name: y\n";
    }
    check(!validate_dat(neg1).empty(), "截断 .dat（缺 Name 行）被拒");
    check(!validate_dat(neg2).empty(), "坏头 .dat（首行非 0 注释）被拒");
    ::remove(neg1.c_str());
    ::remove(neg2.c_str());
    check(!is_regular_file(neg1) && !is_regular_file(neg2), "负向样本已清理");

    std::cout << (failures ? "ldraw_parts_probe: FAILED\n"
                           : "ldraw_parts_probe: all assertions passed\n");
    return failures ? 1 : 0;
}
