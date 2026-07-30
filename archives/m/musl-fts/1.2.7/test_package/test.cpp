#include <stdint.h>
#include <stddef.h>
#include <fts.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>
#include <string>

// musl-fts 1.2.7 —— 真实目录遍历验证（非 dlopen 空壳）。
// OHOS 的 musl sysroot **没有 fts.h**（探针实测），elfutils 又要用它，故补此包。
// 断言：在临时目录里造一棵已知结构的树，用 fts 遍历，逐项核对：
//   ① fts_open / fts_read / fts_close 全程无错
//   ② 遍历到的文件集合与造出来的完全一致（不多不少）
//   ③ 层级深度 fts_level 正确
//   ④ FTS_D / FTS_F 类型判定正确
//   ⑤ fts_set(FTS_SKIP) 真的能剪枝

static int failures = 0;

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__, __LINE__); \
      ++failures;                                                            \
    } else {                                                                 \
      std::printf("[ok] %s\n", msg);                                         \
    }                                                                        \
  } while (0)

static std::string root;

static void mk(const char *rel, bool dir) {
  std::string p = root + "/" + rel;
  if (dir) {
    std::string cmd = "mkdir -p '" + p + "'";
    (void)std::system(cmd.c_str());
  } else {
    std::string cmd = "printf x > '" + p + "'";
    (void)std::system(cmd.c_str());
  }
}

int main() {
  // 不用 /tmp —— 鸿蒙 PC 上应用沙箱里 /tmp 不可写（实测 mkdtemp 直接失败）。
  // 用当前工作目录（conan 的 test_package 目录）建临时树，跑完删掉。
  char tmpl[] = "./ftsprobeXXXXXX";
  const char *d = mkdtemp(tmpl);
  if (!d) {
    std::perror("mkdtemp");
    std::fprintf(stderr, "在当前目录建临时目录失败\n");
    return 1;
  }
  root = d;

  //  root/a/b/deep.txt   root/a/one.txt   root/two.txt   root/skipme/hidden.txt
  mk("a/b", true);
  mk("skipme", true);
  mk("a/b/deep.txt", false);
  mk("a/one.txt", false);
  mk("two.txt", false);
  mk("skipme/hidden.txt", false);

  // ① ② ③ ④ 完整遍历
  {
    char *paths[] = {const_cast<char *>(root.c_str()), nullptr};
    FTS *fts = fts_open(paths, FTS_PHYSICAL | FTS_NOCHDIR, nullptr);
    CHECK(fts != nullptr, "fts_open 成功");
    std::set<std::string> files, dirs;
    int max_level = 0;
    if (fts) {
      FTSENT *e;
      while ((e = fts_read(fts)) != nullptr) {
        const std::string rel = std::string(e->fts_path).substr(root.size());
        if (e->fts_info == FTS_F) {
          files.insert(rel);
          if (e->fts_level > max_level) max_level = e->fts_level;
        } else if (e->fts_info == FTS_D) {
          dirs.insert(rel);
        }
      }
      CHECK(fts_close(fts) == 0, "fts_close 返回 0");
    }
    CHECK(files.size() == 4, "遍历到 4 个普通文件");
    if (files.size() != 4) {
      std::fprintf(stderr, "       实得 %zu 个:", files.size());
      for (const auto &f : files) std::fprintf(stderr, " %s", f.c_str());
      std::fprintf(stderr, "\n");
    }
    CHECK(files.count("/two.txt") && files.count("/a/one.txt")
              && files.count("/a/b/deep.txt") && files.count("/skipme/hidden.txt"),
          "四个文件路径逐一对上");
    CHECK(dirs.count("") && dirs.count("/a") && dirs.count("/a/b") && dirs.count("/skipme"),
          "四个目录（含根）都被访问（FTS_D）");
    CHECK(max_level == 3, "最深文件的 fts_level = 3（a/b/deep.txt）");
    if (max_level != 3) std::fprintf(stderr, "       实得 %d\n", max_level);
  }

  // ⑤ FTS_SKIP 剪枝
  {
    char *paths[] = {const_cast<char *>(root.c_str()), nullptr};
    FTS *fts = fts_open(paths, FTS_PHYSICAL | FTS_NOCHDIR, nullptr);
    int n_files = 0;
    if (fts) {
      FTSENT *e;
      while ((e = fts_read(fts)) != nullptr) {
        if (e->fts_info == FTS_D && std::strcmp(e->fts_name, "skipme") == 0) {
          fts_set(fts, e, FTS_SKIP);
          continue;
        }
        if (e->fts_info == FTS_F) ++n_files;
      }
      fts_close(fts);
    }
    CHECK(n_files == 3, "FTS_SKIP 剪掉 skipme/ 后只剩 3 个文件");
    if (n_files != 3) std::fprintf(stderr, "       实得 %d\n", n_files);
  }

  std::string rm = "rm -rf '" + root + "'";
  (void)std::system(rm.c_str());

  if (failures) {
    std::fprintf(stderr, "\nmusl-fts: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\nmusl-fts 1.2.7: 全部断言通过\n");
  return 0;
}
