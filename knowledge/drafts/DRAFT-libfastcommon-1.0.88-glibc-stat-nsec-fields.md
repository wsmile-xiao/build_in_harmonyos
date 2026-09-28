# DRAFT-libfastcommon-1.0.88-glibc-stat-nsec-fields — glibc 专有 struct stat 纳秒字段在 OHOS musl 缺失

> **Contributor**: pc2-15 | **Status**: DRAFT | **Updated**: 2026-09-22
> **Severity**: 🟡 medium | **Category**: ohos / musl / glibc-isms / struct-stat / portability
> **对应 KV**: DRAFT-libfastcommon-1.0.88-glibc-stat-nsec-fields.kv

## 问题

libfastcommon 上游测试 `src/tests/test_mblock.c` 使用 glibc 专有的
`struct stat` 纳秒字段：

```c
printf("file access time: %d.%ld\n", (int)st.st_atime, st.st_atimensec);
printf("file modify time: %d.%ld\n", (int)st.st_mtime, st.st_mtimensec);
printf("file change time: %d.%ld\n", (int)st.st_ctime, st.st_ctimensec);
```

在 OHOS musl 上编译报错：

```text
test_mblock.c:145:63: error: no member named 'st_atimensec' in 'struct stat'
test_mblock.c:146:63: error: no member named 'st_mtimensec' in 'struct stat'
test_mblock.c:147:63: error: no member named 'st_ctimensec' in 'struct stat'
```

## 根因

glibc 在 `struct stat` 上提供 `st_atimensec/st_mtimensec/st_ctimensec`
（直接成员别名，整数纳秒），而 musl（OHOS libc）只提供 POSIX 标准的
`st_atim.tv_nsec/st_mtim.tv_nsec/st_ctim.tv_nsec`（`struct timespec` 内嵌）。
这是"把 libc 当作 glibc"的惯性写法（glibc-isms），与
E081（secure_getenv）、E493（program_invocation_name）、E203（getprogname）
等 musl 缺失族同源，但本条是 **struct stat 成员形态差异**（非函数/符号缺失）。

## 方案

把 glibc 专有字段替换为 POSIX 标准 `tv_nsec`：

```c
printf("file access time: %d.%ld\n", (int)st.st_atime, (long)st.st_atim.tv_nsec);
printf("file modify time: %d.%ld\n", (int)st.st_mtime, (long)st.st_mtim.tv_nsec);
printf("file change time: %d.%ld\n", (int)st.st_ctime, (long)st.st_ctim.tv_nsec);
```

`tv_nsec` 在 glibc 与 musl 上均存在，修复同时保持两平台可移植。

## 验证

- 修改后 `src/tests` 全部 36 个测试程序编译通过（clang 15，OHOS armv8）；
- `test_mblock` 可运行（30s 上限内无错误输出，SIGTERM 截断为长时基准类）；
- 该修改仅用于本地上游测试运行取证（R51），测试文件非 CI 输入，不进 PR 补丁。

## 适用边界

- 适用于在 OHOS/musl 上编译时使用 `st_atimensec` 等 glibc 专有
  `struct stat` 直接成员的源码（库代码或测试代码）；
- 修复目标必须选 POSIX 标准字段（`tv_nsec`），而非反过来给 musl 补别名宏。

## 反例与限制

- 不得用平台宏 `#ifdef __OHOS__` 双份维护（同字段两种写法），直接采用
  POSIX 标准形态即可，两平台通用；
- 若上游代码同时大量使用其他 glibc 专有 stat 宏（如 `st_mtim` 均已具备），
  按实际缺失字段逐一替换，不要整段重写；
- 本修改只针对测试/示例代码时，注意不要把它混入库本身的可交付源码补丁。
