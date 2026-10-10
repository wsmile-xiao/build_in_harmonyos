// members 消费者测试（rule12 / 鸿蒙特有测试）：
// 被测包安装的 members 可执行文件参与本测试——本程序由 test_package 用 OHOS
// 工具链（musl libc）编译，运行时把 members 当作被测对象拉起，并用同一个 libc
// 的 getgrgid / getgrnam / getpwent 独立算出期望输出，逐字节比对。
//
// 覆盖的 OHOS(musl) 平台差异行为：getopt_long 选项解析、getgrnam 附属组成员、
// getpwent 枚举主组成员、退出码约定、错误信息走 stderr。
//
// 用法: test_members <members 可执行文件路径>
#include <grp.h>
#include <pwd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <string>
#include <vector>

namespace {

int g_checks = 0;
int g_failed = 0;

void check(bool ok, const std::string &what) {
  ++g_checks;
  if (!ok) {
    ++g_failed;
    std::fprintf(stderr, "FAIL: %s\n", what.c_str());
  } else {
    std::printf("ok   : %s\n", what.c_str());
  }
}

struct Result {
  int rc = -1;
  std::string out;
  std::string err;
};

std::string slurp(int fd) {
  std::string s;
  char buf[4096];
  ssize_t n;
  while ((n = read(fd, buf, sizeof buf)) > 0) s.append(buf, (size_t)n);
  return s;
}

// fork+exec 被测程序，分别捕获 stdout / stderr 与退出码
Result run(const std::string &exe, const std::vector<std::string> &args) {
  Result r;
  int po[2], pe[2];
  if (pipe(po) != 0 || pipe(pe) != 0) return r;
  pid_t pid = fork();
  if (pid == 0) {
    dup2(po[1], 1);
    dup2(pe[1], 2);
    close(po[0]); close(po[1]); close(pe[0]); close(pe[1]);
    std::vector<char *> argv;
    argv.push_back(const_cast<char *>(exe.c_str()));
    for (const auto &a : args) argv.push_back(const_cast<char *>(a.c_str()));
    argv.push_back(nullptr);
    execv(exe.c_str(), argv.data());
    _exit(127);
  }
  close(po[1]); close(pe[1]);
  r.out = slurp(po[0]);
  r.err = slurp(pe[0]);
  close(po[0]); close(pe[0]);
  int st = 0;
  waitpid(pid, &st, 0);
  r.rc = WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st);
  return r;
}

std::vector<std::string> tokens(const std::string &line) {
  std::vector<std::string> v;
  std::istringstream is(line);
  std::string t;
  while (is >> t) v.push_back(t);
  return v;
}

bool contains(const std::vector<std::string> &v, const std::string &x) {
  for (const auto &e : v) if (e == x) return true;
  return false;
}

struct GroupInfo {
  std::string name;
  gid_t gid;
  std::vector<std::string> secondary;   // gr_mem
  std::vector<std::string> primary_all;    // 所有 pw_gid == gid 的用户（getpwent 序）
  std::vector<std::string> primary_no_first; // 同上，但去掉 getpwent 首条记录
};

// 在调用其它 getgr*/getpw* 之前把静态缓冲区内容复制走
GroupInfo describe(const struct group *g) {
  GroupInfo gi;
  gi.name = g->gr_name;
  gi.gid = g->gr_gid;
  for (char **m = g->gr_mem; m && *m; ++m) gi.secondary.push_back(*m);
  setpwent();
  bool first = true;
  while (struct passwd *p = getpwent()) {
    if (p->pw_gid == gi.gid) {
      gi.primary_all.push_back(p->pw_name);
      if (!first) gi.primary_no_first.push_back(p->pw_name);
    }
    first = false;
  }
  endpwent();
  return gi;
}

bool same(const std::vector<std::string> &a, const std::vector<std::string> &b) {
  return a == b;
}

// members 对主组成员的枚举会跳过 getpwent 返回的第一条记录（上游
// display_primaries 先多调了一次 getpwent），因此只要求：
//   (primary_all 去掉首条) ⊆ 输出 ⊆ primary_all
void check_primary(const GroupInfo &g, const std::vector<std::string> &got,
                   const std::string &tag) {
  bool subset = true;
  for (const auto &u : got) if (!contains(g.primary_all, u)) subset = false;
  check(subset, tag + ": 主组成员输出 ⊆ libc getpwent(pw_gid==gid)");
  bool superset = true;
  for (const auto &u : g.primary_no_first)
    if (!contains(got, u)) superset = false;
  check(superset, tag + ": 主组成员输出 ⊇ getpwent 除首条外的主组用户");
}

void check_group(const std::string &members, const GroupInfo &g) {
  const std::string t = "group '" + g.name + "'";

  Result s = run(members, {"-s", g.name});
  check(s.rc == 0, t + ": -s 退出码 0");
  check(same(tokens(s.out), g.secondary),
        t + ": -s 输出 == getgrnam().gr_mem（逐项、同序）");
  Result sl = run(members, {"--secondary", g.name});
  check(sl.rc == 0 && sl.out == s.out, t + ": --secondary 与 -s 输出一致");

  Result p = run(members, {"-p", g.name});
  check(p.rc == 0, t + ": -p 退出码 0");
  check(!p.out.empty() && p.out.back() == '\n', t + ": -p 输出以换行结尾");
  std::vector<std::string> ptoks = tokens(p.out);
  check_primary(g, ptoks, t + " -p");

  Result tl = run(members, {"-t", g.name});
  check(tl.rc == 0, t + ": -t 退出码 0");
  // -t 始终输出两行（即使没有任何成员），第一行主组、第二行附属组
  std::string first = tl.out.substr(0, tl.out.find('\n'));
  check(std::count(tl.out.begin(), tl.out.end(), '\n') == 2,
        t + ": -t 恰好两行（主组行 + 附属组行）");
  check(same(tokens(first), ptoks), t + ": -t 第一行 == -p 输出");
  std::string second;
  {
    size_t a = tl.out.find('\n');
    size_t b = tl.out.find('\n', a + 1);
    if (a != std::string::npos && b != std::string::npos)
      second = tl.out.substr(a + 1, b - a - 1);
  }
  check(same(tokens(second), g.secondary),
        t + ": -t 第二行 == getgrnam().gr_mem");

  Result a = run(members, {"-a", g.name});
  std::vector<std::string> expect = ptoks;
  expect.insert(expect.end(), g.secondary.begin(), g.secondary.end());
  check(same(tokens(a.out), expect),
        t + ": -a 输出 == 主组成员 + 附属组成员");
  // 上游约定：组存在但没有任何成员时 -a 返回 1（悬空 else），否则返回 0
  check(a.rc == (expect.empty() ? 1 : 0),
        t + ": -a 退出码与成员是否为空一致");
  Result d = run(members, {g.name});
  check(d.rc == a.rc && d.out == a.out, t + ": 缺省模式 == -a");
}

}  // namespace

int main(int argc, char **argv) {
  if (argc != 2) {
    std::fprintf(stderr, "usage: %s <path-to-members>\n", argv[0]);
    return 2;
  }
  const std::string members = argv[1];

  // 被测程序必须真实存在且可执行
  check(access(members.c_str(), X_OK) == 0, "members 可执行文件存在且有执行位");

  // 1. --help：退出码 0，输出选项说明
  Result h = run(members, {"--help"});
  check(h.rc == 0, "--help 退出码 0");
  check(h.out.find("--two-lines") != std::string::npos &&
            h.out.find("SEE ALSO: man members") != std::string::npos,
        "--help 输出含选项说明与 SEE ALSO");

  // 2. 缺少组名参数：退出码 1，usage 走 stderr
  Result n = run(members, {});
  check(n.rc == 1 && n.err.find("Usage:") != std::string::npos &&
            n.out.empty(),
        "无参数：退出码 1，Usage 写 stderr、stdout 为空");

  // 3. 不存在的组：退出码 1，错误信息走 stderr
  const std::string ghost = "no-such-group-ohos-members";
  check(getgrnam(ghost.c_str()) == nullptr, "前置：libc 也认为该组不存在");
  Result g = run(members, {ghost});
  check(g.rc == 1 && g.out.empty() &&
            g.err.find("members: group " + ghost + " does not exist") !=
                std::string::npos,
        "不存在的组：退出码 1，stderr 给出 does not exist");
  Result gt = run(members, {"-t", ghost});
  check(gt.rc == 1, "不存在的组 -t：退出码 1");

  // 4. 用 libc 独立算出期望，对真实存在的组逐项比对
  std::vector<GroupInfo> groups;
  if (struct group *mine = getgrgid(getgid())) groups.push_back(describe(mine));
  // 再挑一个有附属组成员的组（若系统里有），覆盖 gr_mem 非空路径
  setgrent();
  while (struct group *gr = getgrent()) {
    if (gr->gr_mem && gr->gr_mem[0]) {
      bool dup = false;
      for (const auto &x : groups) if (x.gid == gr->gr_gid) dup = true;
      if (!dup) {
        groups.push_back(describe(gr));
        break;
      }
    }
  }
  endgrent();
  if (groups.empty())
    std::printf("NOTE : 本机组数据库里没有可用组，跳过依赖 libc 期望值的比对\n");
  for (const auto &gi : groups) check_group(members, gi);

  std::printf("checks=%d failed=%d\n", g_checks, g_failed);
  return g_failed == 0 ? 0 : 1;
}
