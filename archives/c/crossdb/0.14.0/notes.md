# crossdb 0.14.0 适配笔记

## 编译环境

- 构建系统: cmake（上游 CMakeLists.txt；另有裸 Makefile，选 CMake 是因为它一步装齐库 + 头 + CLI 并可接 CTest）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4（aarch64-linux-ohos, OHOS 26.0.0.18 SDK）
- CMake: 4.1.2 / Conan: 2.29.x / GNU Make: 4.4.1
- 状态: built

## 编译步骤

```bash
# 1. 源码与身份（W0）
git ls-remote --tags https://github.com/crossdb-org/crossdb.git   # 14 个 tag 全量命中，含 0.14.0（无 v 前缀）
curl -LO https://github.com/crossdb-org/crossdb/archive/refs/tags/0.14.0.tar.gz
sha256sum 0.14.0.tar.gz
#   38c79686481d2f324ce3d48fcf559f8ea4700e7ed3fa01f7ff9e38bfc79d8572
#   == codeload.github.com 同 tag 下载 == conan-center-index recipes/crossdb/all/conandata.yml 公布值

# 2. 探索性构建（打补丁前先复现问题，打补丁后复现修复）
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DXDB_BUILD_TESTS=ON
cmake --build build -j4
ctest --build-dir build --verbose      # 1/1 Test #1: xdb_smoke_test Passed；125 cases 全绿

# 3. Conan 配方验证（采信轮）
sh tools/conan_verify_round.sh crossdb 0.14.0 --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案（补丁） |
|---|------|------|------|
| 1 | `src/lib/xdb_str.c:146: use of undeclared identifier 'REG_STARTEND'`（编译硬错） | musl 的 `<regex.h>` 没有 BSD 扩展 `REG_STARTEND`；而 `REGEXP` 的被匹配串是「长度前缀切片」，并非 NUL 结尾 | `0002`：`#ifdef REG_STARTEND` 保留原路径，`#else` 先把 `len` 字节复制成 NUL 结尾缓冲区再 `regexec` |
| 2 | `src/core/xdb_crud.c:2140: implicit declaration of 'qsort_r'` + 链接未定义符号 | musl libc 不导出 glibc 风格 `qsort_r(base,n,size,compar,arg)`（`nm -D libc.so` 只有 `qsort`）；`ORDER BY` 必经此函数 | `0003`：`#if !defined(__GLIBC__) && …` 下提供本地 shim，用 `__thread` 上下文委托 `qsort`（crossdb 服务器是多线程，故用线程局部而非静态全局，E531 fallback 口径） |
| 3 | 每个带 `PRIMARY KEY` 的 `CREATE TABLE`（含 sysdb 自举的 5 张系统表）都报 `Duplicate PRIMARY KEY`，冒烟套件 125 例首轮 **0 通过** | **AArch64 上 plain `char` 默认无符号**（实测 `CHAR_MIN=0 CHAR_MAX=255`）：`xdb_stmt_tbl_t.pkey_idx` 是 `char`，`pkey_idx = -1` 存成 255，`XDB_EXPECT(pkey_idx < 0)` 恒假 | `0004`：字段声明改为 `signed char`（最小外科修复；不采用全局 `-fsigned-char`，因为 crossline 的字节处理在上游就依赖无符号语义，全局翻转会引入新的未定义行为面） |
| 4 | 文件库一律建不出来：`Can't fallocate fd N length 616(+616) -> err 13 Permission denied`，`CREATE DATABASE` 返回 `XDB_E_FILE(11)` | HMDFS/tmpfs 不支持 `posix_fallocate(2)`，返回 EACCES；探针实测 `posix_fallocate rc=13` 而 `ftruncate rc=0`（E523 同族） | `0005`：`posix_fallocate` 失败时回退 `ftruncate(fd, length)`（与上游 `__APPLE__` 分支同一做法） |
| 5 | `xdb-cli` 任何带参数的调用都挂死（`timeout 5` 得 124） | `char ch; while ((ch = getopt(...)) != -1)`：无符号 `char` 把 getopt 的 -1 变成 255，`255 != -1` 恒真 | `0006`：`ch` 改为 `int`（getopt 契约本身要求 int） |
| 6 | L2 冒烟门禁会判失败（`xdb-cli --version` 与 `--help` 都返回 255） | 两者都不在 `getopt` 的 optstring 里，走 `case '?'` 后 `return -1`（E503 同族） | `0006`（同补丁第 2 处）：在 getopt 循环前拦截 GNU 长选项，打印版本 / 用法后 `return 0` |
| 7 | 上游测试无法被配方自动执行（`test/Makefile` 手写 `-lcrossdb`，conan 侧拿不到编译器与库路径） | 上游 CMakeLists 没有测试目标 | `0001`：新增 `XDB_BUILD_TESTS`（默认 OFF，不改上游默认行为）注册 CTest 目标，配方 `generate()` 打开、`build()` 里 `ctest --verbose` |

## 源码修改

全部适配均落在补丁里，配方本身不改源码（无 `replace()`、无 `__OHOS__`、无 `-D` 平台宏注入）：

| 补丁 | 目标文件 | 类型 |
|---|---|---|
| `0001-cmake-smoke-test-target.patch` | `CMakeLists.txt` | portability |
| `0002-regex-reg-startend-fallback.patch` | `src/lib/xdb_str.c` | portability |
| `0003-qsort-r-thread-local-shim.patch` | `src/core/xdb_crud.c` | compatibility |
| `0004-signed-char-pkey-idx.patch` | `src/parser/xdb_stmt.h` | portability |
| `0005-posix-fallocate-ftruncate-fallback.patch` | `src/lib/xdb_file.c` | portability |
| `0006-xdb-cli-getopt-and-long-options.patch` | `src/xdb-cli.c` | portability |

配方层（conanfile.py）只做两件配置：`BUILD_SHARED_LIBS`（默认静态）与
`XDB_BUILD_TESTS=ON`。

## 依赖版本

无外部依赖（上游 0 deps）。工具链：clang 15.0.4、cmake 4.1.2、conan 2.29.x、GNU Make 4.4.1。

## 测试口径

- **上游**：`test/xdb_smoke_test.c` + `test/utest.h`
  - 源码宏数：`UTEST_I(` 57 处 + `UTEST_F(` 11 处 = 68 处
  - 框架注册数：57×2 + 11 = **125** 个运行期用例（`UTEST_I` 的第三个参数 INDEX=2）
  - assertion 数：**203** 处 `ASSERT_*` / `EXPECT_*`
  - **N = 候选数法最大值 = 203**（四口径不混用，差额逐项归因）
- **消费者（鸿蒙特有测试行）**：`test_package/test.c` **28** 项 CHECK 断言
- 详见 `reports/test-report.md`

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` | Conan 配方（CMake，静态默认，build() 跑 ctest） |
| `conandata.yml` | 源 URL + sha256 + 6 个补丁声明 |
| `patches/*.patch` | 6 个 HarmonyOS 可移植性补丁 |
| `test_package/` | 消费者测试（28 项断言）+ MANIFEST.yml |
| `manifest.yaml` / `notes.md` | 交叉校验元数据与本笔记 |
