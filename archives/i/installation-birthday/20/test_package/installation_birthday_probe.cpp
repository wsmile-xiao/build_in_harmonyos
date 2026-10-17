// installation_birthday_probe.cpp — installation-birthday/20 消费者探针
//
// 静态断言：argv[1] = 包根目录。验证纯脚本包载荷的完整性：
//   组1 包内清单（2 文件精确，排除 conan 簿记）
//   组2 脚本内容锚点（14 项：shebang/GPL-3 头/行为字符串/参数/v20 候选）
//   组3 COPYING 锚点（3 项：GPL-3 全文本特征）
//   组4 静态完整性（脚本 226 行 + COPYING 674 行精确、无 CR、末行锚点）
//   组5 负向注入（截断/CR 污染副本被拒，恢复计数）
// 运行语义（--help/--verbosity 5/--force --puppet 全跑）由同目录
// test_behavior.py 负责（需 python3，真机 3.12.9 已具备）。
#include <cstdio>
#include <cstring>
#include <dirent.h>
#include <fstream>
#include <sstream>
#include <string>
#include <sys/stat.h>
#include <unistd.h>

// conan 2 会在包根写入 conaninfo.txt/conanmanifest.txt 簿记文件
// （真机实测），全树计数时排除，使计数口径只覆盖配方安装的载荷。
static bool is_bookkeeping(const std::string& name) {
    return name == "conaninfo.txt" || name == "conanmanifest.txt";
}

static int count_recursive(const std::string& dir) {
    int n = 0;
    DIR* d = opendir(dir.c_str());
    if (!d) return -1;
    struct dirent* e;
    while ((e = readdir(d)) != nullptr) {
        std::string name = e->d_name;
        if (name == "." || name == "..") continue;
        std::string full = dir + "/" + name;
        struct stat info;
        if (stat(full.c_str(), &info) != 0) continue;
        if (S_ISDIR(info.st_mode)) {
            int sub = count_recursive(full);
            if (sub < 0) { closedir(d); return -1; }
            n += sub;
        } else if (S_ISREG(info.st_mode) && !is_bookkeeping(name)) {
            ++n;
        }
    }
    closedir(d);
    return n;
}

static bool read_file(const std::string& path, std::string& out) {
    std::ifstream f(path.c_str(), std::ios::binary);
    if (!f) return false;
    std::ostringstream ss;
    ss << f.rdbuf();
    out = ss.str();
    return true;
}

static bool file_exists_nonempty(const std::string& path) {
    struct stat info;
    return stat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode)
           && info.st_size > 0;
}

static int count_lines(const std::string& s) {
    int n = 0;
    for (size_t i = 0; i < s.size(); ++i) if (s[i] == '\n') ++n;
    return n;
}

static bool has(const std::string& hay, const std::string& needle) {
    return hay.find(needle) != std::string::npos;
}

static int g_fail = 0;

static void check(bool ok, const std::string& what) {
    printf("[%s] %s\n", ok ? "OK" : "FAIL", what.c_str());
    if (!ok) ++g_fail;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <package_root>\n", argv[0]);
        return 2;
    }
    const std::string root = argv[1];
    const std::string script = root + "/bin/installation-birthday";
    const std::string docdir = root + "/share/doc/installation-birthday";
    const std::string copying = docdir + "/COPYING";

    // ---- 组1 包内清单 ----
    check(file_exists_nonempty(script),
          "bin/installation-birthday 在位非空");
    check(file_exists_nonempty(copying),
          "share/doc/installation-birthday/COPYING 在位非空");
    check(count_recursive(root + "/bin") == 1, "bin/ 恰 1 文件");
    check(count_recursive(docdir) == 1, "share/doc/installation-birthday/ 恰 1 文件");
    check(count_recursive(root) == 2, "包全树恰 2 文件（排除 conan 簿记）");

    std::string s, c;
    check(read_file(script, s), "读取脚本内容");
    check(read_file(copying, c), "读取 COPYING 内容");

    // ---- 组2 脚本内容锚点（14 项）----
    check(has(s, "#!/usr/bin/env python3"), "shebang");
    // "Copyright © 2017-2020 Chris Lamb"（UTF-8 版权符号按字节断言）
    check(has(s, std::string("Copyright \xC2\xA9 2017-2020 Chris Lamb <lamby@debian.org>")),
          "2017-2020 Chris Lamb 版权行");
    check(has(s, "GNU General Public License as published by"),
          "GPL 头（Free Software Foundation 措辞）");
    check(has(s, "either version 3 of the License"), "GPL-3+ 条款锚点");
    check(has(s, "Receive congratulations on system installation anniversaries"),
          "DESCRIPTION 字符串");
    check(has(s, "H a p p y"), "蛋糕模板 Happy 行");
    check(has(s, "B i r t h d a y ! ! !"), "蛋糕模板 Birthday!!! 行");
    check(has(s, "--verbosity"), "--verbosity 参数");
    check(has(s, "--puppet"), "--puppet 参数");
    check(has(s, "--force"), "--force 参数");
    check(has(s, "/var/log/installer"), "候选时间戳 /var/log/installer");
    check(has(s, "/etc/hostname"), "候选时间戳 /etc/hostname（v20 新增）");
    check(has(s, "datetime.UTC"), "datetime.UTC（需 python3.11+）");
    check(has(s, "if __name__ == \"__main__\":"), "主入口守卫");

    // ---- 组3 COPYING 锚点 ----
    check(has(c, "GNU GENERAL PUBLIC LICENSE"), "COPYING 标题");
    check(has(c, "Version 3, 29 June 2007"), "GPL-3 版本行");
    check(has(c, "Free Software Foundation"), "FSF 条款锚点");

    // ---- 组4 静态完整性 ----
    check(count_lines(s) == 226, "脚本恰 226 行");
    check(count_lines(c) == 674, "COPYING 恰 674 行");
    check(!has(s, "\r") && !has(c, "\r"), "两文件均无 CR（LF 发行）");
    check(has(s, "sys.exit(Birthday().main())"), "末行入口调用锚点");

    // ---- 组5 负向注入（副本上验证拒绝，不动包内载荷）----
    {
        const std::string neg1 = "probe_neg_truncated.py";
        {
            std::string half = s.substr(0, s.size() / 2);
            std::ofstream f(neg1.c_str(), std::ios::binary);
            f << half;
        }
        std::string t;
        bool truncated_detected =
            read_file(neg1, t)
            && (count_lines(t) != 226 || !has(t, "sys.exit(Birthday().main())"));
        check(truncated_detected, "截断副本被检出（行数/末行锚点失配）");

        const std::string neg2 = "probe_neg_cr.py";
        {
            std::string cr = s;
            for (size_t i = 0; i < cr.size(); ++i) if (cr[i] == '\n') cr[i] = '\r';
            std::ofstream f(neg2.c_str(), std::ios::binary);
            f << cr;
        }
        std::string t2;
        bool cr_detected = read_file(neg2, t2) && has(t2, "\r");
        check(cr_detected, "CR 污染副本被检出");

        remove(neg1.c_str());
        remove(neg2.c_str());
        check(!file_exists_nonempty(neg1) && !file_exists_nonempty(neg2),
              "负向副本清理，包内计数不受影响");
        check(count_recursive(root) == 2, "清理后包全树仍恰 2 文件");
    }

    if (g_fail == 0) {
        printf("installation_birthday_probe: all assertions passed\n");
        return 0;
    }
    printf("installation_birthday_probe: %d assertion(s) FAILED\n", g_fail);
    return 1;
}
