# dirent 1.26：OHOS 上游 C 测试源码双探针适配（libc 探针 + $TMPDIR 探针）

> Draft: DRAFT-DIRENT-1.26-OHOS-UPSTREAM-TEST-LIBC-PROBE-TMPDIR
> Stem: `DRAFT-DIRENT-1.26-OHOS-UPSTREAM-TEST-LIBC-PROBE-TMPDIR` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-DIRENT-1.26-OHOS-UPSTREAM-TEST-LIBC-PROBE-TMPDIR
- **严重度**: 2
- **类别**: ohos|testing|libc|musl|portability
- **触发工具**: ctest|conan create|cc|make check
- **阶段**: testing

## 问题特征（真实日志片段）

dirent 1.26（tronkko/dirent，纯头文件 + CMake INTERFACE 库）在 OHOS PC
(arm64, musl libc, Clang 15) 上 `conan create` 时，9 个上游 CTest 中 3 个
编译/运行失败：

```
# t-strverscmp.c → 链接失败
ld.lld: error: undefined symbol: strverscmp
>>> referenced by t-strverscmp.c: CMakeFiles/t-strverscmp.dir/tests/t-strverscmp.c.o:(main)

# t-scandir.c → 编译失败
tests/t-scandir.c:166:53: error: use of undeclared identifier 'versionsort'
        int n = scandir("tests/3", &files, no_directories, versionsort);

# t-symlink.c / t-scandir.c test_large → 运行失败
Cannot create directory /tmp/feokycgunu        ← mkdir("/tmp/...", 0700) 失败
Assertion failed: ok == 0 (.../test_large: 305) ← 1000 文件用例 mkdir 失败
```

## 根因

1. **musl 缺 GNU 扩展符号**：`strverscmp()`/`versionsort()` 是 glibc 的
   GNU/BSD 扩展，musl（OHOS 运行时 libc）明确不实现。dirent 自带
   `include/dirent.h` 内有可移植实现（Windows 上给 MSVC 用），但非 Windows
   平台上 CMakeLists 不给测试链接该头（系统 dirent.h 胜出），测试直接调用
   系统符号 → 链接/编译失败。
2. **/tmp 只读**：OHOS PC 的 `/tmp` 是 `erofs (ro)` 只读挂载。上游测试源码
   硬编码 `strcpy(dirname, "/tmp/")` 拼接临时目录，不读 TMPDIR 环境变量，
   结果 `mkdir("/tmp/xxx", 0700)` 恒失败。E002 的"设 TMPDIR 环境变量"方案
   对硬编码路径的测试源码无效。
3. **PATH_MAX 未声明**：musl 不隐式传递 `<limits.h>`，`t-symlink.c` 用
   `PATH_MAX` 未包含头文件 → 编译错误。

> 注：E132/E134/E136 等既有条目覆盖 configure/config.status 临时目录场景；
> 本条目聚焦**上游测试源码**（CMake CTest 可执行测试）的编译/运行适配，
> 与 configure 场景同族不同位。

## 修复方案（rec，实测通过）

### A. libc 探针兜底 GNU 扩展（t-strverscmp.c / t-scandir.c）

在测试文件 include 区后插入，用宏映射把缺失的 GNU 扩展指向 dirent 自带
可移植实现（函数体与 `include/dirent.h` 中 strverscmp 逐字一致）：

```c
#if !defined(__GLIBC__) && !defined(_MSC_VER)
static int dirent_portable_strverscmp(const char *a, const char *b)
{
    size_t i = 0, j;
    while (a[i] == b[i]) { if (a[i] == '\0') return 0; ++i; }
    j = i; while (j > 0 && isdigit(a[j-1])) --j;
    if (a[j] == '0' || b[j] == '0') { ...前导零语义... }
    else if (isdigit(a[j]) && isdigit(b[j])) { ...数字长度语义... }
    return (int)((unsigned char)a[i]) - ((unsigned char)b[i]);
}
static int dirent_portable_versionsort(const struct dirent **a,
                                       const struct dirent **b)
{ return dirent_portable_strverscmp((*a)->d_name, (*b)->d_name); }
#define strverscmp dirent_portable_strverscmp
#define versionsort dirent_portable_versionsort
#endif
```

- glibc 平台编译时不定义宏 → 走系统实现，行为零差异；
- 是 **libc 探针**（`__GLIBC__` 探测），按 R8 例外在 PR 说明理由；
- 不伪造测试：断言全部保留，实测 t-strverscmp PASS、t-scandir PASS。

### B. $TMPDIR 探针替换硬编码 `/tmp/`（t-symlink.c / t-scandir.c test_large）

```c
{
    const char *td = getenv("TMPDIR");
    if (td != NULL && *td != '\0') {
        size_t len = strlen(td);
        if (len + 1 < (size_t) PATH_MAX) {
            memcpy(base, td, len);
            if (td[len-1] != '/') base[len++] = '/';
            base[len] = '\0'; i = (int) len;
        } else { strcpy(base, "/tmp/"); i = strlen(base); }
    } else { strcpy(base, "/tmp/"); i = strlen(base); }
}
```

同时补 `#include <limits.h>`（PATH_MAX/PATH_MAX+1 需要，musl 不隐式传递）。

### C. 构建侧注入可写 TMPDIR

conanfile.py `build()` / `test()`：在 build_folder 建专用目录并设环境变量：

```python
test_tmp = os.path.join(self.build_folder, "test-tmp")
os.makedirs(test_tmp, exist_ok=True)
os.environ["TMPDIR"] = os.environ["TMP"] = os.environ["TEMP"] = test_tmp
```

（OHOS PC 无可用可写 + 保留 0700 语义的独立挂载点——/dev/shm、/data/local/tmp、
/storage/Users 顶层均不可写或 HMDFS 不保留 0700；build_folder 在 HMDFS 上但
测试只 mkdir+写文件，不 stat 断言 0700，可行。）

## 验证（本轮实测）

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64` → exit 0
  9 个 CTest 全部实例化: 7 pass + 2 skip（t-unicode/t-utf8 为上游 `#ifdef WIN32`
  专测，非本条目引入，不计失败）→ 可执行集 7/7 = 100%
- 关键命令/退出码/日志 SHA-256 见 dirent archives/d/dirent/1.26 notes.md
  双口径台账（source_declared_total=9, executed_passed_total=7）

## 与既有条目边界（四范围查重）

| 条目 | 覆盖部分 | 本条目新增/边界 |
|---|---|---|
| E534 (busybox musl GNU 扩展兼容层) | musl 缺 strverscmp 根因 + weak 符号/配置规避（库侧） | 上游**测试源码**侧 libc 探针兜底 + dirent 自带实现复用（测试侧，非库侧） |
| E093/E094/E081 (getpass/pthread_affinity/secure_getenv) | musl 缺 GNU/glibc 扩展 → source-patch 同族 | 具体符号 strverscmp/versionsort + 测试上下文 |
| E002 (/tmp erofs 只读 → 设 TMPDIR) | /tmp 只读根因（environment 层） | 硬编码路径测试源码的**代码级** $TMPDIR 探针（env 变量对它无效） |
| DRAFT-8959-libei (musl tmpfile 硬编码 /tmp) | 代码级 $TMPDIR 替代（libc 函数侧 tmpfile()） | 测试源码**字面路径** "/tmp/" 拼接场景（非 tmpfile 调用） |
| DRAFT-6507-cln-mktemp-0700-hmdfs | mktemp 0700/HMDFS 权限 | 本条目不 stat 断言 0700，仅 mkdir+写 |

- exact_duplicate: 否（测试源码侧双探针组合无同款）。
- causal_duplicate: 部分——根因（musl 缺 GNU 扩展 / /tmp 只读）与既有条目相同。
- trigger_overlap: 高（error_signature 大量重叠：undefined symbol: strverscmp、
  Cannot create directory /tmp）。引擎口径可将本条目并入 E534/E002 的
  match_keywords；但测试上下文（CMake CTest 源码）是新增触发面。
- solution_overlap: 中——E534 建议库内 weak 符号，E002 建议环境变量；
  本条目是测试文件 side-car 补丁 + 构建侧 env 注入，三者正交可组合。
- combination_novelty: 有——"libc 探针 + $TMPDIR 探针"在单个上游测试套件内
  组合处理，且给出 test 侧可移植实现复用（dirent.h 自带函数体），可跨库套用。
- boundary_novelty: 有——明确划分"测试源码"（本条目）vs "configure/config.status
  临时目录"（E136/E052）vs "libc tmpfile()"（DRAFT-8959）vs "库侧 weak 符号"
  （E534）。
- test_migration_novelty: 有——把 E534/E002 的既有知识迁移到上游测试源码适配
  的准确操作（#include <limits.h> 修正 + 探针补丁 + 构建 env 注入），
  全量测试 9/9 实例化、7/7 可执行集通过，台账可追溯。

## 适用判断

- **适用**：OHOS/musl 上 CMake/CTest 套件内测试源码直接调用 strverscmp/
  versionsort（或同类缺符号 GNU 扩展）、硬编码 /tmp 路径、或 PATH_MAX 未
  包含 limits.h 时。
- **不适用**：configure/config.status 临时目录问题（E136/E052）；musl
  tmpfile() 调用侧（DRAFT-8959）；库自身二进制缺符号（走 E534 库侧 weak
  符号）；非测试代码的 GNU 扩展调用（走 E093/E094 类）。
- 反例：测试框架若已自行定义宏或链接 fexecve 兼容库，则探针补丁会重复定义
  → 应先核对上游已有 HAVE_STRVERSCMP 类守卫。