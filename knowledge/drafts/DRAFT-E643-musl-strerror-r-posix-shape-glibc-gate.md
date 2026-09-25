# DRAFT-E643 — musl strerror_r 恒为 POSIX 形态：GNU 分支判据换 __GLIBC__

- **触发**：`const char *p = strerror_r(errno, buf, sizeof buf);` 在
  `#elif defined(_GNU_SOURCE)` 分支——musl（OHOS libc）只提供 POSIX/XSI
  形态（返回 `int`），`_GNU_SOURCE` 不改变它；clang 报
  `incompatible integer to pointer conversion`（硬错误；gcc 仅警告）。
- **修复**：GNU 形态分支判据 `_GNU_SOURCE` → `__GLIBC__`（glibc 专属库身份
  宏，musl 全形态未定义）；其余平台（musl/BSD/macOS）走 XSI 臂：
  `/* int ret = */ strerror_r(errno, buf, sizeof buf); p = buf;`
- **红线**：不要 `#elif defined(__OHOS__)`（移植补丁禁新增平台宏，PF5）；
  `__GLIBC__` 判据对 OHOS 之外的所有 musl 发行版同样正确。
- **验收**：补丁 apply 后 `make` 编过 error.c；`grep __GLIBC__` 命中判据行。
- **实例**：`archives/p/pev/0.82` patches/0001-lib-libpe-error.c.patch
  （conan create 干净轮 G2 PASS）。
