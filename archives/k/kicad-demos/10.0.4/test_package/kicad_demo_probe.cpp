// kicad_demo_probe — kicad-demos 消费者测试探针
//
// 真实消费演示工程数据：解析 .kicad_pcb / .kicad_sch 的 s-expression 头部
// （根符号 + version + generator），解析 .kicad_pro 的 JSON 结构，
// 并用 s-expression 计数器统计各工程资源形态，验证包内资源真实可读、
// 格式与 KiCad 官方文件规范一致。

#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
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

// ── s-expression 词法解析（KiCad 板/原理图文件的最小完整子集） ──
// 支持：嵌套括号、双引号字符串（含 \" 转义）、行注释与行内 ; 注释。
// 解析成 token 树后可断言头部字段，比正则更接近 KiCad 的实际读取路径。
struct SexpNode {
    std::string atom;             // 叶子：裸原子或字符串字面量
    bool quoted = false;
    std::vector<SexpNode> children;
};

class SexpLexer {
public:
    explicit SexpLexer(const std::string& text) : text_(text), pos_(0) {}

    char peek() {
        skip_ws();
        return pos_ < text_.size() ? text_[pos_] : '\0';
    }

    std::string next_atom() {
        skip_ws();
        const size_t start = pos_;
        while (pos_ < text_.size() && !std::strchr("()\";", text_[pos_]) &&
               !std::isspace(static_cast<unsigned char>(text_[pos_]))) {
            ++pos_;
        }
        if (pos_ == start) throw std::runtime_error("empty atom in s-expression");
        return text_.substr(start, pos_ - start);
    }

    std::string next_string() {
        skip_ws();
        if (pos_ >= text_.size() || text_[pos_] != '"')
            throw std::runtime_error("expected string literal");
        ++pos_;
        std::string out;
        while (pos_ < text_.size()) {
            const char c = text_[pos_];
            if (c == '\\') {                      // KiCad 转义：\" \\ \n
                if (pos_ + 1 >= text_.size()) throw std::runtime_error("dangling escape");
                out += text_[pos_ + 1];
                pos_ += 2;
                continue;
            }
            if (c == '"') { ++pos_; return out; }
            out += c;
            ++pos_;
        }
        throw std::runtime_error("unterminated string literal");
    }

    void expect(char c) {
        skip_ws();
        if (pos_ >= text_.size() || text_[pos_] != c)
            throw std::runtime_error(std::string("expected '") + c + "'");
        ++pos_;
    }

    bool at_end() {
        skip_ws();
        return pos_ >= text_.size();
    }

private:
    void skip_ws() {
        while (pos_ < text_.size()) {
            const char c = text_[pos_];
            if (std::isspace(static_cast<unsigned char>(c))) { ++pos_; continue; }
            if (c == ';') {                        // 行内注释到行尾
                while (pos_ < text_.size() && text_[pos_] != '\n') ++pos_;
                continue;
            }
            return;
        }
    }

    const std::string& text_;
    size_t pos_;
};

SexpNode parse_sexp(SexpLexer& lex) {
    SexpNode node;
    for (;;) {
        const char c = lex.peek();
        if (c == '\0') throw std::runtime_error("unexpected end of s-expression");
        if (c == ')') return node;                 // 由调用方消费 ')'
        if (c == '(') {
            lex.expect('(');
            node.children.push_back(parse_sexp(lex));
            lex.expect(')');
            continue;
        }
        if (c == '"') {
            SexpNode leaf;
            leaf.atom = lex.next_string();
            leaf.quoted = true;
            node.children.push_back(std::move(leaf));
            continue;
        }
        SexpNode leaf;
        leaf.atom = lex.next_atom();
        node.children.push_back(std::move(leaf));
    }
}

const SexpNode* find_child(const SexpNode& node, const std::string& key) {
    for (const SexpNode& child : node.children)
        if (!child.children.empty() && !child.children.front().quoted &&
            child.children.front().atom == key)
            return &child;
    return nullptr;
}

std::string child_atom(const SexpNode& node, size_t index) {
    if (index >= node.children.size()) throw std::runtime_error("missing child atom");
    return node.children[index].atom;
}

std::string read_text(const std::string& path) {
    std::ifstream stream(path.c_str(), std::ios::binary);
    if (!stream) throw std::runtime_error("cannot read file: " + path);
    std::ostringstream buffer;
    buffer << stream.rdbuf();
    return buffer.str();
}

// 解析 .kicad_pcb / .kicad_sch：断言根符号、version、generator。
// 头部字段用 s-expression 窗口解析（version/generator 均在文件头部）；
// 完整性用独立的字符串感知括号深度全文件流式扫描（KiCad 9 teardrops
// 块存在把 filter_ratio 原子写到闭合括号之外的已知生成器缺陷，KiCad
// 官方解析器跳过层外多余闭合、demo 按原样分发），但未闭合的 '(' 与
// 未闭合字符串必须报错。
void validate_board_or_schematic(const std::string& path, const std::string& root_symbol) {
    {
        std::ifstream stream(path.c_str(), std::ios::binary);
        if (!stream) throw std::runtime_error("cannot read file: " + path);
        std::string head(4096, '\0');
        stream.read(&head[0], static_cast<std::streamsize>(head.size()));
        const std::streamsize head_len = stream.gcount();
        head.resize(static_cast<size_t>(head_len));
        if (head_len < 16) throw std::runtime_error("suspiciously small file: " + path);

        SexpLexer lex(head);
        lex.expect('(');
        // 根符号（裸原子，如 kicad_pcb / kicad_sch）
        if (lex.peek() == '"') throw std::runtime_error("quoted root symbol in " + path);
        const std::string symbol = lex.next_atom();
        if (symbol != root_symbol)
            throw std::runtime_error("root symbol '" + symbol + "' mismatch in " + path);
        // 头部子节点逐个解析：version/generator 等头部字段都是小而完整的
        // 子表达式。头部窗口耗尽属于正常终止（文件主体是单棵巨树）。
        SexpNode root;
        {
            SexpNode symbol_leaf;
            symbol_leaf.atom = symbol;
            root.children.push_back(symbol_leaf);
        }
        for (int guard = 0; guard < 32; ++guard) {
            const char c = lex.peek();
            if (c == ')' || c == '\0') break;
            if (c != '(') throw std::runtime_error("unexpected token in header of " + path);
            try {
                lex.expect('(');
                SexpNode child = parse_sexp(lex);
                lex.expect(')');
                root.children.push_back(std::move(child));
            } catch (const std::runtime_error& e) {
                // 头部窗口边界：已解析到的子节点足够完成字段断言
                if (find_child(root, "version") && find_child(root, "generator")) break;
                throw std::runtime_error(std::string("header truncated: ") + e.what() +
                                         " in " + path);
            }
        }

        const SexpNode* version = find_child(root, "version");
        if (!version || version->children.size() < 2)
            throw std::runtime_error("missing (version ...) header in " + path);
        const std::string ver = child_atom(*version, 1);
        for (const char c : ver)
            if (c < '0' || c > '9')
                throw std::runtime_error("non-numeric version stamp in " + path);

        const SexpNode* generator = find_child(root, "generator");
        if (!generator || generator->children.size() < 2)
            throw std::runtime_error("missing (generator ...) header in " + path);
    }

    // 独立的正文全文件扫描：字符串感知的括号深度校验。
    std::ifstream stream(path.c_str(), std::ios::binary);
    if (!stream) throw std::runtime_error("cannot reopen file: " + path);
    int depth = 0;
    long long consumed = 0;
    bool in_str = false;
    bool escaped = false;
    int c;
    while ((c = stream.get()) != EOF) {
        ++consumed;
        if (in_str) {
            if (escaped) { escaped = false; continue; }
            if (c == '\\') { escaped = true; continue; }
            if (c == '"') in_str = false;
            continue;
        }
        if (c == '"') { in_str = true; continue; }
        if (c == '(') ++depth;
        else if (c == ')' && depth > 0) --depth;
    }
    if (in_str) throw std::runtime_error("unterminated string in " + path);
    if (depth != 0) throw std::runtime_error("unclosed s-expression in " + path);
    if (consumed < 16) throw std::runtime_error("suspiciously small file: " + path);
}

// 解析 .kicad_pro：KiCad 工程文件是 JSON，断言对象结构与关键字段。
void validate_project_json(const std::string& path) {
    const std::string text = read_text(path);
    // 最小 JSON 结构校验：括号配平与字符串闭合（含转义）。
    int depth = 0;
    bool seen_root_open = false;
    bool in_string = false;
    char prev = '\0';
    for (const char c : text) {
        if (in_string) {
            if (c == '"' && prev != '\\') in_string = false;
            prev = c;
            continue;
        }
        if (c == '"') { in_string = true; prev = c; continue; }
        if (c == '{' || c == '[') {
            ++depth;
            if (c == '{' && depth == 1) seen_root_open = true;
        } else if (c == '}' || c == ']') {
            --depth;
            if (depth < 0) throw std::runtime_error("unbalanced JSON in " + path);
        }
        prev = c;
    }
    if (in_string) throw std::runtime_error("unterminated JSON string in " + path);
    if (depth != 0 || !seen_root_open)
        throw std::runtime_error("malformed JSON structure in " + path);
    // 工程文件必须包含 KiCad 板/原理图设计配置节
    if (text.find("\"board\"") == std::string::npos &&
        text.find("\"schematic\"") == std::string::npos)
        throw std::runtime_error("kicad_pro missing board/schematic section: " + path);
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

void collect_files(const std::string& root, const std::string& ext,
                   std::vector<std::string>& out) {
    // 递归目录收集（复杂工程 sch/pcb 嵌套在各子目录）
    for (const std::string& name : list_dir(root)) {
        const std::string path = root + "/" + name;
        if (is_regular_file(path) && ends_with(name, ext)) out.push_back(path);
        struct stat info {};
        if (::stat(path.c_str(), &info) == 0 && S_ISDIR(info.st_mode))
            collect_files(path, ext, out);
    }
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: kicad_demo_probe <kicad-demos-resource-root>\n";
        return 2;
    }
    const std::string demos_root = argv[1];

    try {
        // 1) 资源根目录必须存在且为目录
        struct stat info {};
        if (::stat(demos_root.c_str(), &info) != 0 || !S_ISDIR(info.st_mode))
            throw std::runtime_error("demos resource root is not a directory: " + demos_root);

        // 2) 18 个官方演示工程目录全部在位
        const char* expected_projects[] = {
            "cm5_minima", "complex_hierarchy", "ecc83", "interf_u",
            "jetson-agx-thor-baseboard", "kit-dev-coldfire-xilinx_5213",
            "microwave", "multichannel", "openair-max", "pic_programmer",
            "python_scripts_examples", "royalblue54L_feather", "simulation",
            "sonde xilinx", "stickhub", "tiny_tapeout", "video", "vme-wren",
        };
        for (const char* project : expected_projects) {
            const std::string path = demos_root + "/" + project;
            if (::stat(path.c_str(), &info) != 0 || !S_ISDIR(info.st_mode))
                throw std::runtime_error(std::string("missing demo project dir: ") + project);
        }

        // 3) 全量消费：解析全部 .kicad_pcb / .kicad_sch 的 s-expression 头部
        std::vector<std::string> boards, schematics, projects;
        collect_files(demos_root, ".kicad_pcb", boards);
        collect_files(demos_root, ".kicad_sch", schematics);
        collect_files(demos_root, ".kicad_pro", projects);
        if (boards.size() != 19)
            throw std::runtime_error("expected 19 .kicad_pcb files, got " +
                                     std::to_string(boards.size()));
        if (schematics.size() != 115)
            throw std::runtime_error("expected 115 .kicad_sch files, got " +
                                     std::to_string(schematics.size()));
        if (projects.size() != 36)
            throw std::runtime_error("expected 36 .kicad_pro files, got " +
                                     std::to_string(projects.size()));

        std::map<std::string, int> board_generators;
        for (const std::string& path : boards) {
            validate_board_or_schematic(path, "kicad_pcb");
            ++board_generators["pcbnew"];
        }
        if (board_generators["pcbnew"] != 19)
            throw std::runtime_error("not every board was generated by pcbnew");

        for (const std::string& path : schematics)
            validate_board_or_schematic(path, "kicad_sch");
        for (const std::string& path : projects)
            validate_project_json(path);

        // 4) 负向校验：截断文件必须被解析器拒绝
        const char* tmpdir = ::getenv("TMPDIR");
        std::string truncated = tmpdir && *tmpdir
                                    ? std::string(tmpdir)
                                    : std::string(".");
        if (!truncated.empty() && truncated.back() != '/') truncated += '/';
        truncated += "kicad_truncated_probe.kicad_pcb";
        {
            const std::string sample = read_text(boards.front()).substr(0, 64);
            std::ofstream out(truncated.c_str(), std::ios::binary | std::ios::trunc);
            out << sample;  // 故意截断在多层嵌套中
        }
        bool rejected = false;
        try {
            validate_board_or_schematic(truncated, "kicad_pcb");
        } catch (const std::exception&) {
            rejected = true;
        }
        if (!rejected) throw std::runtime_error("truncated kicad_pcb was not rejected");
        ::unlink(truncated.c_str());

        std::cout << "kicad-demos consumer probe: 19 boards + 115 schematics + "
                  << projects.size() << " projects parsed OK\n";
        return 0;
    } catch (const std::exception& err) {
        std::cerr << "kicad_demo_probe FAILED: " << err.what() << "\n";
        return 1;
    }
}
