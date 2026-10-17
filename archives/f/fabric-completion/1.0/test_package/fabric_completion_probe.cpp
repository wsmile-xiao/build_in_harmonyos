// fabric_completion_probe — fabric-completion 1 消费者测试探针
//
// 真实消费 fabric-completion 数据包：校验 completions/ 与 doc/ 目录
// 清单，逐项断言补全脚本与 README 的内容锚点（shebang、MIT 条款、
// 缓存配置、__fab_completion 函数、complete 注册行等），并做行数
// 精确计数与 CR 检测，附截断/坏注册行注入负向用例——证明包内数据
// 真实可读且内容与上游 commit 5b59104 发行一致。
//
// 用法: fabric_completion_probe <package-root>

#include <dirent.h>
#include <sys/stat.h>

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

namespace {

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

long count_lines(const std::string& text) {
    long n = 0;
    for (char c : text)
        if (c == '\n') ++n;
    if (!text.empty() && text[text.size() - 1] != '\n') ++n;  // 末行无换行
    return n;
}

int count_files(const std::string& dir) {
    DIR* d = ::opendir(dir.c_str());
    if (!d) return -1;
    int n = 0;
    dirent* e;
    while ((e = ::readdir(d))) {
        std::string name = e->d_name;
        if (name == "." || name == "..") continue;
        if (is_regular_file(dir + "/" + name)) ++n;
    }
    ::closedir(d);
    return n;
}

// conan 2 会在包根写入 conaninfo.txt/conanmanifest.txt 簿记文件
// （真机实测），全树计数时排除，使计数口径只覆盖配方安装的载荷。
bool is_bookkeeping(const std::string& name) {
    return name == "conaninfo.txt" || name == "conanmanifest.txt";
}

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
        else if (S_ISREG(info.st_mode) && !is_bookkeeping(name)) ++n;
    }
    ::closedir(d);
    return n;
}

// 单文件补全脚本校验：shebang + complete 注册行 + 无 CR；
// 通过返回空串，否则返回失败原因。
std::string validate_script(const std::string& path) {
    std::string text = read_file(path);
    if (!starts_with(text, "#!/usr/bin/env bash")) return "bad shebang";
    if (text.find('\r') != std::string::npos) return "CRLF";
    if (!contains(text, "complete -o default -o nospace -F __fab_completion fab"))
        return "missing complete registration";
    return "";
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
        std::cerr << "usage: fabric_completion_probe <package-root>\n";
        return 2;
    }
    const std::string root = argv[1];
    const std::string completions = root + "/share/bash-completion/completions";
    const std::string script = completions + "/fabric-completion.bash";
    const std::string doc = root + "/share/doc/fabric-completion";
    const std::string readme = doc + "/README.md";

    std::cout << "== [1/5] 包内清单 (2 文件) ==\n";
    check(is_regular_file(script), "completions/fabric-completion.bash 在位");
    check(is_regular_file(readme), "doc/fabric-completion/README.md 在位");
    check(count_files(completions) == 1, "completions/ 恰 1 文件");
    check(count_files(doc) == 1, "doc/fabric-completion/ 恰 1 文件");
    check(count_recursive(root) == 2, "包全树恰 2 文件（排除 conan 簿记）");

    std::cout << "== [2/5] 脚本内容锚点 ==\n";
    const std::string s = read_file(script);
    check(starts_with(s, "#!/usr/bin/env bash"), "shebang: #!/usr/bin/env bash");
    check(contains(s, "Copyright (C) 2011 by Konstantin Bakulin"), "2011 Bakulin 版权行");
    check(contains(s, "THE SOFTWARE IS PROVIDED \"AS IS\""), "MIT 条款全文");
    check(contains(s, "export FAB_COMPLETION_CACHE_TASKS=true"), "缓存开关环境变量");
    check(contains(s, "FAB_COMPLETION_CACHED_TASKS_FILENAME=\".fab_tasks~\""),
          ".fab_tasks~ 缓存文件名");
    check(contains(s, "function __fab_completion()"), "__fab_completion 函数");
    check(contains(s, "fab --shortlist"), "fab --shortlist 任务列表调用");
    check(contains(s, "fab --help"), "fab --help 长选项调用");
    check(contains(s, "compgen -W"), "compgen 补全生成");
    check(contains(s, "__fab_chache_mtime"), "上游原样拼写 __fab_chache_mtime");
    check(contains(s, "__fab_fabfile_mtime"), "__fab_fabfile_mtime 辅助函数");
    check(contains(s, "Darwin|FreeBSD"), "uname 平台分支 (Darwin|FreeBSD)");

    std::cout << "== [3/5] README 锚点 ==\n";
    const std::string r = read_file(readme);
    check(contains(r, "# Bash completion for [Fabric](http://fabfile.org)"),
          "README 标题 (fabfile.org)");
    check(contains(r, "## Features"), "README Features 节");
    check(contains(r, "## Installation"), "README Installation 节");
    check(contains(r, "source /path/to/file/fabric-completion.bash"),
          "README source 指令行");
    check(contains(r, "## Settings"), "README Settings 节");
    check(contains(r, "FAB_COMPLETION_CACHE_TASKS=false"), "README 缓存开关设置");
    check(contains(r, "FAB_COMPLETION_CACHED_TASKS_FILENAME"),
          "README 缓存文件名设置");

    std::cout << "== [4/5] 静态完整性 (124/46 行精确) ==\n";
    check(count_lines(s) == 124, "脚本 124 行精确");
    check(count_lines(r) == 46, "README 46 行精确");
    check(validate_script(script).empty(), "脚本校验通过 (shebang+注册行+LF)");
    {
        std::istringstream in(s);
        std::string last, line;
        while (std::getline(in, line)) last = line;
        check(last == "complete -o default -o nospace -F __fab_completion fab",
              "脚本末行 = complete 注册行");
    }

    std::cout << "== [5/5] 截断/坏注册行注入负向 ==\n";
    const std::string neg1 = completions + "/__probe_neg1__.bash";
    const std::string neg2 = completions + "/__probe_neg2__.bash";
    {
        std::ofstream out(neg1, std::ios::binary);
        out << "#!/usr/bin/env bash\n# truncated\n";
    }
    {
        std::ofstream out(neg2, std::ios::binary);
        out << "#!/usr/bin/env bash\ncomplete -F some_other_fn fab\n";
    }
    check(!validate_script(neg1).empty(), "截断脚本（无注册行）被拒");
    check(!validate_script(neg2).empty(), "坏注册行脚本被拒");
    ::remove(neg1.c_str());
    ::remove(neg2.c_str());
    check(!is_regular_file(neg1) && !is_regular_file(neg2), "负向样本已清理");
    check(count_files(completions) == 1, "清理后 completions/ 恢复 1 文件");

    std::cout << (failures ? "fabric_completion_probe: FAILED\n"
                           : "fabric_completion_probe: all assertions passed\n");
    return failures ? 1 : 0;
}
