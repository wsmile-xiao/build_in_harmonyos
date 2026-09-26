// mypaint_brush_probe — mypaint-brushes 2.0.2 消费者测试探针
//
// 真实消费包内笔刷数据（通过 dep.cpp_info.resdirs 定位 share/mypaint-data/
// 2.0/brushes）：
//   1. 7 个上游笔刷组目录齐全（Dieterle/classic/deevad/experimental/
//      kaerhon_v1/ramon/tanda）
//   2. order.conf 每个条目逐一映射到磁盘 .myb 文件（order<->disk 互证）
//   3. 全部 .myb 文件均为合法纯 JSON（'{' 开头 + 括号/字符串配平，本
//      2.0.2 tarball 实测 196/196 为纯 JSON，非 gzip）
// 与 kicad-demos 10.0.4 的 kicad_demo_probe 同款范式（R34 实质校验）。

#include <dirent.h>
#include <sys/stat.h>

#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

bool is_dir(const std::string& path) {
    struct stat info {};
    return ::stat(path.c_str(), &info) == 0 && S_ISDIR(info.st_mode);
}

bool is_file(const std::string& path) {
    struct stat info {};
    return ::stat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode);
}

std::vector<std::string> list_dir(const std::string& root) {
    std::vector<std::string> names;
    DIR* dir = ::opendir(root.c_str());
    if (!dir) throw std::runtime_error("cannot open directory: " + root);
    while (dirent* entry = ::readdir(dir)) {
        const std::string name(entry->d_name);
        if (name == "." || name == "..") continue;
        names.push_back(name);
    }
    ::closedir(dir);
    return names;
}

void collect_myb(const std::string& root, std::vector<std::string>& out) {
    for (const std::string& name : list_dir(root)) {
        const std::string path = root + "/" + name;
        if (is_file(path)) {
            if (name.size() > 4 && name.substr(name.size() - 4) == ".myb")
                out.push_back(path);
        } else if (is_dir(path)) {
            collect_myb(path, out);
        }
    }
}

bool is_ws(char c) {
    return c == ' ' || c == '\t' || c == '\r' || c == '\n';
}

// 最小 JSON 配平校验（字符串感知），足够验证 .myb 笔刷文件真实可读。
bool json_balanced(const std::string& text) {
    bool in_string = false, escaped = false;
    int depth = 0;
    for (const char c : text) {
        if (in_string) {
            if (escaped) { escaped = false; continue; }
            if (c == '\\') { escaped = true; continue; }
            if (c == '"') in_string = false;
            continue;
        }
        if (c == '"') { in_string = true; continue; }
        if (c == '{' || c == '[') ++depth;
        else if (c == '}' || c == ']') {
            --depth;
            if (depth < 0) return false;
        }
    }
    return !in_string && depth == 0;
}

std::string read_text(const std::string& path) {
    std::ifstream stream(path.c_str(), std::ios::binary);
    if (!stream) throw std::runtime_error("cannot read file: " + path);
    std::string out((std::istreambuf_iterator<char>(stream)),
                    std::istreambuf_iterator<char>());
    return out;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: mypaint_brush_probe <brushes-resource-root>\n";
        return 2;
    }
    const std::string brushes = argv[1];

    try {
        // 1) 资源根目录必须存在
        if (!is_dir(brushes))
            throw std::runtime_error("brushes root is not a directory: " + brushes);

        // 2) 7 个上游笔刷组目录全部在位
        const char* groups[] = {"Dieterle", "classic", "deevad", "experimental",
                                "kaerhon_v1", "ramon", "tanda"};
        for (const char* g : groups) {
            const std::string path = brushes + "/" + g;
            if (!is_dir(path))
                throw std::runtime_error(std::string("missing brush group dir: ") + g);
        }

        // 3) order.conf <-> disk 互证：每个条目都有对应 .myb 文件
        const std::string order_path = brushes + "/order.conf";
        if (!is_file(order_path))
            throw std::runtime_error("order.conf missing: " + order_path);
        std::ifstream order(order_path.c_str());
        if (!order) throw std::runtime_error("cannot read order.conf");
        int entries = 0, missing = 0;
        std::string line;
        while (std::getline(order, line)) {
            if (line.empty() || line[0] == '#' || line.compare(0, 6, "Group:") == 0)
                continue;
            // 跳过纯空白行
            bool blank = true;
            for (const char c : line) if (!is_ws(c)) { blank = false; break; }
            if (blank) continue;
            ++entries;
            if (!is_file(brushes + "/" + line + ".myb")) {
                ++missing;
                if (missing <= 5)
                    std::cerr << "  missing .myb for order.conf entry: " << line << "\n";
            }
        }
        if (entries < 190)
            throw std::runtime_error("order.conf has only " + std::to_string(entries) +
                                     " entries (expected >=190)");
        if (missing != 0)
            throw std::runtime_error(std::to_string(missing) + "/" +
                                     std::to_string(entries) +
                                     " order.conf entries have no .myb on disk");

        // 4) 全部 .myb 为纯 JSON 且可读
        std::vector<std::string> mybs;
        collect_myb(brushes, mybs);
        if (mybs.size() < 190)
            throw std::runtime_error("expected >=190 .myb files, got " +
                                     std::to_string(mybs.size()));
        int plain_json = 0;
        for (const std::string& path : mybs) {
            const std::string text = read_text(path);
            // MyPaint 2.x 笔刷为 gzip JSON 或纯 JSON；本 2.0.2 tarball
            // 实测 196/196 为纯 JSON（'{' 开头）。两种合法格式均接受。
            const bool is_gzip = text.size() >= 2 &&
                                 static_cast<unsigned char>(text[0]) == 0x1f &&
                                 static_cast<unsigned char>(text[1]) == 0x8b;
            const bool is_json = text.size() >= 2 && text[0] == '{';
            if (is_gzip) continue;
            if (!is_json)
                throw std::runtime_error("unexpected .myb format (not gzip/JSON): " + path);
            if (!json_balanced(text))
                throw std::runtime_error("unbalanced JSON in .myb: " + path);
            ++plain_json;
        }

        std::cout << "mypaint-brushes consumer probe: " << entries
                  << " order.conf entries resolved, " << mybs.size()
                  << " .myb files read OK (" << plain_json << " plain JSON)\n";
        return 0;
    } catch (const std::exception& err) {
        std::cerr << "mypaint_brush_probe FAILED: " << err.what() << "\n";
        return 1;
    }
}
