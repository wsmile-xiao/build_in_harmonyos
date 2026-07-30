#include <stdint.h>
#include <stddef.h>
#include <obstack.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

// musl-obstack 1.2.3 —— 真实 obstack 分配验证（非 dlopen 空壳）。
// OHOS 的 musl sysroot **没有 obstack.h**（探针实测），elfutils 大量使用它，故补此包。
// obstack 是 glibc 的"栈式增长对象"分配器，语义特殊，必须真用一遍：
//   ① obstack_init / obstack_alloc 基本分配，写入后内容正确
//   ② obstack_grow 增量拼接 → 一次 obstack_finish 取出完整对象
//   ③ 多个对象共存且互不干扰（obstack 的核心语义）
//   ④ obstack_free 回退到指定对象，之后可继续分配
//   ⑤ obstack_object_size 报告正在构造的对象大小
//   ⑥ 大对象跨 chunk（超过初始 chunk）仍然连续可读

#define obstack_chunk_alloc malloc
#define obstack_chunk_free  free

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

int main() {
  struct obstack ob;
  obstack_init(&ob);

  // ①
  {
    char *p = static_cast<char *>(obstack_alloc(&ob, 16));
    CHECK(p != nullptr, "obstack_alloc(16) 返回非空");
    if (p) {
      std::memcpy(p, "0123456789abcde", 16);
      CHECK(std::strncmp(p, "0123456789abcde", 15) == 0, "写入后内容正确");
    }
  }

  // ② ⑤ 增量增长
  {
    obstack_grow(&ob, "hello", 5);
    CHECK(obstack_object_size(&ob) == 5, "obstack_object_size 在 grow 5 字节后为 5");
    obstack_grow(&ob, ", ", 2);
    obstack_grow(&ob, "world", 5);
    obstack_1grow(&ob, '\0');
    CHECK(obstack_object_size(&ob) == 13, "累计 grow 后大小为 13");
    char *s = static_cast<char *>(obstack_finish(&ob));
    CHECK(s != nullptr && std::strcmp(s, "hello, world") == 0,
          "obstack_finish 取出拼接结果 \"hello, world\"");
    if (s && std::strcmp(s, "hello, world") != 0)
      std::fprintf(stderr, "       实得 \"%s\"\n", s);
  }

  // ③ 多对象共存
  {
    obstack_grow(&ob, "AAAA", 4); obstack_1grow(&ob, '\0');
    char *a = static_cast<char *>(obstack_finish(&ob));
    obstack_grow(&ob, "BBBBBB", 6); obstack_1grow(&ob, '\0');
    char *b = static_cast<char *>(obstack_finish(&ob));
    CHECK(a && b && std::strcmp(a, "AAAA") == 0 && std::strcmp(b, "BBBBBB") == 0,
          "两个对象共存、内容互不干扰");
    CHECK(a != b, "两个对象地址不同");
  }

  // ⑥ 大对象跨 chunk（远大于默认 chunk 大小）
  {
    const size_t N = 300000;
    for (size_t i = 0; i < N; ++i)
      obstack_1grow(&ob, static_cast<char>('a' + (i % 26)));
    obstack_1grow(&ob, '\0');
    CHECK(obstack_object_size(&ob) == N + 1, "大对象累计大小正确");
    char *big = static_cast<char *>(obstack_finish(&ob));
    bool ok = big != nullptr;
    if (ok)
      for (size_t i = 0; i < N; i += 4093)      // 抽样但跨越所有 chunk 边界
        if (big[i] != static_cast<char>('a' + (i % 26))) { ok = false; break; }
    CHECK(ok, "跨 chunk 的 300000 字节对象内容连续正确");
  }

  // ④ obstack_free 回退
  {
    char *mark = static_cast<char *>(obstack_alloc(&ob, 8));
    char *later = static_cast<char *>(obstack_alloc(&ob, 8));
    CHECK(mark && later, "回退前两次分配成功");
    obstack_free(&ob, mark);            // 回退到 mark（含 mark 本身被释放）
    char *again = static_cast<char *>(obstack_alloc(&ob, 8));
    CHECK(again != nullptr, "obstack_free 回退后仍可继续分配");
    std::memset(again, 0x5A, 8);
    CHECK(static_cast<unsigned char>(again[7]) == 0x5A, "回退后新分配的内存可写");
  }

  obstack_free(&ob, nullptr);           // 全部释放

  if (failures) {
    std::fprintf(stderr, "\nmusl-obstack: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\nmusl-obstack 1.2.3: 全部断言通过\n");
  return 0;
}
