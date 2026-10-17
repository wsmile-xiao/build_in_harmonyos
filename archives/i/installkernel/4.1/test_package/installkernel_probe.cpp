// installkernel 4.1 消费者探针：包内清单 / 内容锚点 / 静态完整性 /
// 行为烟测 / 注入负向，共 5 组断言（2026-09-26，alpine aports
// commit 69a2ca2b 钉死口径）。
#include <dirent.h>
#include <sys/stat.h>
#include <sys/types.h>

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#ifdef _WIN32
#include <direct.h>
#else
#include <unistd.h>  // ::rmdir
#endif

static int g_fail = 0;
static int g_skip = 0;

static void check(bool ok, const std::string& msg) {
    std::cout << "  [" << (ok ? "OK" : "FAIL") << "]   " << msg << "\n";
    if (!ok) ++g_fail;
}

static void skip(const std::string& msg) {
    std::cout << "  [SKIP]  " << msg << "\n";
    ++g_skip;
}

static bool is_regular_file(const std::string& path) {
    struct stat st {};
    return ::stat(path.c_str(), &st) == 0 && S_ISREG(st.st_mode);
}

// 写权限实测的临时目录选取：鸿蒙真机 /tmp 只读（G2 实测），
// 依次探测 TMPDIR/TMP/TEMP，全不可写则回落当前目录。
static std::string pick_temp_dir() {
    const char* envs[] = {"TMPDIR", "TMP", "TEMP"};
    for (const char* e : envs) {
        const char* v = std::getenv(e);
        if (!v || !*v) continue;
        const std::string base = v;
        const std::string probe = base + "/.ikprobe-" +
                                  std::to_string((long)::time(nullptr));
#ifdef _WIN32
        if (::_mkdir(probe.c_str()) == 0) { ::_rmdir(probe.c_str()); return base; }
#else
        if (::mkdir(probe.c_str(), 0755) == 0) { ::rmdir(probe.c_str()); return base; }
#endif
    }
    return ".";
}

static std::string read_file(const std::string& path) {
    std::ifstream in(path.c_str(), std::ios::binary);
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

static bool write_file(const std::string& path, const std::string& data) {
    std::ofstream out(path.c_str(), std::ios::binary | std::ios::trunc);
    out << data;
    return out.good();
}

static int count_files(const std::string& dir) {
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
// （真机实测，fabric-completion 同款坑），全树计数时排除。
static bool is_bookkeeping(const std::string& name) {
    return name == "conaninfo.txt" || name == "conanmanifest.txt";
}

static long count_recursive(const std::string& dir) {
    long n = 0;
    DIR* d = ::opendir(dir.c_str());
    if (!d) return -1;
    dirent* e;
    while ((e = ::readdir(d))) {
        std::string name = e->d_name;
        if (name == "." || name == "..") continue;
        std::string path = dir + "/" + name;
        struct stat st {};
        if (::stat(path.c_str(), &st) != 0) continue;
        if (S_ISDIR(st.st_mode)) n += count_recursive(path);
        else if (S_ISREG(st.st_mode) && !is_bookkeeping(name)) ++n;
    }
    ::closedir(d);
    return n;
}

// 脚本校验：shebang + Usage 行 + exit 0 末行 + 无 CR；
// 通过返回空串，否则返回失败原因。
static std::string validate_script(const std::string& text) {
    if (text.find('\r') != std::string::npos)
        return "CR 换行（上游为 LF 发行）";
    if (text.rfind("#!/bin/sh", 0) != 0)
        return "shebang 不是 #!/bin/sh";
    if (text.find("Usage: installkernel <version> <image> <System.map> <directory>")
        == std::string::npos)
        return "Usage 行缺失/被改";
    // 末行必须是 exit 0（上游 45 行以 exit 0 收尾）。
    std::string tail = text.size() >= 7 ? text.substr(text.size() - 7) : "";
    if (tail.find("exit 0") == std::string::npos)
        return "末行 exit 0 缺失（疑似截断）";
    return "";
}

// 行为烟测：sh -n 语法 + 0 参数干跑（预期 Usage + exit 1）。
// 仅 POSIX 环境实跑（Linux CI / 鸿蒙真机）；Windows 构建下 sh 与
// /tmp 的路径语义在 MinGW 中不可靠，直接 SKIP。
static void run_behavior_smoke(const std::string& script_path) {
#ifdef _WIN32
    (void)script_path;
    skip("行为烟测在 Windows 构建跳过（真机/CI POSIX 环境实跑）");
    return;
#else
    if (std::system("sh -c ':' >/dev/null 2>&1") != 0) {
        skip("行为烟测需要 sh 环境");
        return;
    }
    const std::string tmp = pick_temp_dir() + "/installkernel-probe";
    ::mkdir(tmp.c_str(), 0755);
    std::string out = tmp + "/out.txt", code = tmp + "/code.txt";
    // 1) 语法检查：sh -n 零告警。
    std::string cmd1 = "sh -n \"" + script_path + "\" >\"" + out + "\" 2>&1; echo $? >\"" + code + "\"";
    std::system(cmd1.c_str());
    std::string rc1 = read_file(code);
    bool syntax_ok = !rc1.empty() && rc1[0] == '0';
    check(syntax_ok, "sh -n 语法零告警");
    // 2) 0 参数干跑：预期 exit 1 且输出 Usage。
    std::string cmd2 = "sh \"" + script_path + "\" >\"" + out + "\" 2>&1; echo $? >\"" + code + "\"";
    std::system(cmd2.c_str());
    std::string rc2 = read_file(code);
    std::string usage_out = read_file(out);
    check(!rc2.empty() && rc2[0] == '1', "0 参数干跑 exit 1");
    check(usage_out.find("Usage: installkernel") != std::string::npos,
          "干跑输出含 Usage 行");
    ::remove(code.c_str());
    ::remove(out.c_str());
#endif
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: installkernel_probe <package-root>\n";
        return 2;
    }
    const std::string root = argv[1];
    const std::string sbin = root + "/sbin";
    const std::string script = sbin + "/installkernel";

    std::cout << "== [1/5] 包内清单 ==\n";
    check(is_regular_file(script), "sbin/installkernel 在位");
    check(!read_file(script).empty(), "sbin/installkernel 非空");
    check(count_files(sbin) == 1, "sbin/ 恰 1 文件");
    check(count_recursive(root) == 1, "包全树恰 1 文件（排除 conan 簿记）");

    const std::string text = read_file(script);

    std::cout << "== [2/5] 脚本内容锚点 ==\n";
    check(text.find("#!/bin/sh") == 0, "shebang: #!/bin/sh");
    check(text.find("set -e") != std::string::npos, "set -e 出错即停");
    check(text.find("Usage: installkernel <version> <image> <System.map> <directory>")
          != std::string::npos, "Usage 行精确");
    check(text.find("${4:-/boot}") != std::string::npos, "destdir 缺省 /boot");
    check(text.find("$i.old") != std::string::npos, ".old 备份逻辑");
    check(text.find("vmlinuz${suffix}") != std::string::npos,
          "vmlinuz[${suffix}] 复制");
    check(text.find("System.map-${kernelrelease}") != std::string::npos,
          "System.map-${kernelrelease} 复制");
    check(text.find("config-${kernelrelease}") != std::string::npos,
          "config-${kernelrelease} 复制");
    check(text.find("kernel-suffix") != std::string::npos,
          "kernel-suffix 写入逻辑");

    std::cout << "== [3/5] 静态完整性（918 字节 / 45 行精确）==\n";
    check(text.size() == 918, "918 字节精确");
    long nl = 0;
    for (char c : text) if (c == '\n') ++nl;
    check(nl == 45, "45 行精确");
    check(validate_script(text).empty(), "脚本校验通过（shebang+Usage+exit 0+LF）");
    check(text.rfind("#!/bin/sh", 0) == 0 &&
          text.size() >= 7 && text.substr(text.size() - 7) == "exit 0\n",
          "首行 shebang + 末行 exit 0");

    std::cout << "== [4/5] 行为烟测（sh -n + 0 参数干跑）==\n";
    run_behavior_smoke(script);

    std::cout << "== [5/5] 截断/坏 Usage 注入负向 ==\n";
    // 负向样本写临时目录（pick_temp_dir 写权限实测，不污染包根；
    // 鸿蒙真机 /tmp 只读，回落当前目录）。
    const std::string tmpdir = pick_temp_dir() + "/installkernel-probe-neg";
#ifdef _WIN32
    ::_mkdir(tmpdir.c_str());
#else
    ::mkdir(tmpdir.c_str(), 0755);
#endif
    const std::string t1 = tmpdir + "/truncated.sh";
    // 截断：去掉末行 exit 0。
    std::string truncated = text;
    std::string::size_type pos = truncated.rfind("exit 0");
    if (pos != std::string::npos) truncated.resize(pos);
    write_file(t1, truncated);
    check(!validate_script(read_file(t1)).empty(), "截断脚本（无 exit 0）被拒");
    // 坏 Usage：替换 Usage 行为错误文本。
    std::string bad = text;
    std::string::size_type u = bad.find("Usage: installkernel");
    std::string::size_type ue = bad.find('\n', u);
    if (u != std::string::npos && ue != std::string::npos)
        bad.replace(u, ue - u, "Usage: totally-wrong");
    std::string t2 = tmpdir + "/bad-usage.sh";
    write_file(t2, bad);
    check(!validate_script(read_file(t2)).empty(), "坏 Usage 行脚本被拒");
    ::remove(t1.c_str());
    ::remove(t2.c_str());
    check(!is_regular_file(t1) && !is_regular_file(t2), "负向样本已清理");
    check(count_files(sbin) == 1, "清理后 sbin/ 恢复 1 文件");

    std::cout << "\ninstallkernel_probe: "
              << (g_fail == 0 ? "all assertions passed"
                              : "FAILED")
              << (g_skip ? "（含 SKIP）" : "") << "\n";
    return g_fail == 0 ? 0 : 1;
}
