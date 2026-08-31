# execstack 20130503 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-24
- 编译器: clang/clang++ (15.0.4)
- 状态: published (W3 conan create 验证通过)

## 软件说明

execstack 是 prelink 20130503 包的一部分，是设置/查询 ELF 二进制可执行栈标志的 CLI 工具。
源码位于 prelink 源码包的 `src/execstack.c`，通过 `bin_PROGRAMS = execstack` 构建。
prelink 包同时包含 prelink 和 execstack 两个工具，但 prelink 需要 GLOB_BRACE 等 glibc 独有特性，
在 musl/OHOS 环境下无法编译，因此只构建 execstack。

## 编译步骤

1. 下载 prelink-20130503.tar.bz2 源码包
2. `conan install --requires=elfutils/0.195 --requires=argp-standalone/1.5.0` 获取依赖
3. 设置 CPPFLAGS/LDFLAGS 指向 elfutils/argp-standalone 的 include/lib 路径
4. 修补 configure 的 umask 077 → 022（OHOS 文件系统限制）
5. `./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
6. `make execstack` （只构建 execstack 目标，跳过 prelink）
7. 手动复制 `src/execstack` 到安装目录 `bin/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | error.h not found | musl libc 不提供 GNU error.h | 创建 patches/add-error-h.patch，添加最小 error.h 替代实现 |
| 2 | argp.h not found | musl libc 不提供 argp.h | 通过 elfutils/0.195 依赖链引入 argp-standalone/1.5.0 |
| 3 | GLOB_BRACE undeclared | musl glob.h 不定义 GLOB_BRACE (glibc 扩展) | 只构建 execstack 目标（不构建 prelink，prelink 的 gather.c 需要 GLOB_BRACE） |
| 4 | config.sub 不识别 aarch64 | 2002 年的 config.sub 太旧 | 使用 --build=aarch64-unknown-linux-gnu（config.sub 能识别 gnu 但不识别 musl） |
| 5 | config.status Permission denied | OHOS 文件系统下 umask 077 创建的临时目录(0700)无法写入 | 修补 configure 将 umask 077 → 022 |
| 6 | program_invocation_name undefined | musl libc 不提供此符号 | error.h 替代实现中使用静态字符串 "execstack" |
| 7 | AC_LIBELF_SXWORD 测试失败 | 运行时测试找不到 libzstd.so.1 | 设置 LD_LIBRARY_PATH 包含所有依赖库路径 |

## 源码修改

### patches/add-error-h.patch
- 新增 `src/error.h` — GNU error.h 的最小替代实现
- 提供 `void error(int status, int errnum, const char *format, ...)` 函数
- musl libc 不提供 error.h，所有 prelink 源文件都 include <error.h>

### configure 运行时修补（在 conanfile.py build() 中）
- `umask 077` → `umask 022`：OHOS 文件系统下 umask 077 创建的目录权限为 0700，
  config.status 无法在其中创建临时文件

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| elfutils | 0.195 | 提供 libelf.h, gelf.h, libelf.so |
| argp-standalone | 1.5.0 | 提供 argp.h, libargp.a（通过 elfutils 依赖链引入） |
| musl-obstack | 1.2.3 | 提供 obstack.h, libobstack.so（通过 elfutils 依赖链引入） |
| musl-fts | 1.2.7 | 提供 fts.h, libfts.so（通过 elfutils 依赖链引入） |
| zstd | 1.5.7 | libelf.so 的运行时依赖 |

## 验证结果

```bash
$ ./execstack --version
execstack 1.0

$ ./execstack --help
Usage: execstack [OPTION...]
execstack -- program to query or set executable stack flag

  -c, --clear-execstack      Clear executable stack flag bit
  -q, --query                Query executable stack flag bit
  -s, --set-execstack        Set executable stack flag bit
  -?, --help                 Give this help list
      --usage                Give a short usage message
  -V, --version              Print program version
```

## 注意事项

1. **只构建 execstack**：prelink 工具本身无法在 musl/OHOS 上编译（需要 GLOB_BRACE），
   conanfile.py 中 `make target="execstack"` 只构建 execstack 二进制。
2. **aarch64 架构限制**：execstack 上游不支持 aarch64 ELF 文件（无 arch-aarch64.c），
   查询 aarch64 二进制时会报 "architecture is not supported"。这是上游限制，非编译问题。
3. **动态链接依赖**：execstack 运行时需要 libelf.so、libargp.so、libobstack.so、libfts.so、
   libzstd.so，这些通过 Conan 依赖管理自动解析。
---

**编译结束**: 2026-08-24 10:20
**最终状态**: built

## 上游测试用例调查（2026-08-24）

### 调查方法
解压官方源码包 `prelink-20130503.tar.bz2`，检查 testsuite/ 目录及所有 Makefile.am 中的 TESTS 目标。

### 调查结论：execstack 无上游测试用例

prelink 源码包包含完整的 `testsuite/` 目录（约 100 个文件），但经逐项排查：

1. **testsuite/ 全部针对 prelink 工具**：
   - `testsuite/functions.sh` 仅定义 `run_prelink`、`run_prelink_tree` 等辅助函数
   - `testsuite/Makefile.am` 的 TESTS 列表全部是 prelink 回归测试脚本
   - 案例名均为 `prelink-*.sh` 形式（如 `prelink-1.sh` ~ `prelink-*.sh`）

2. **grep 全仓搜索结果**：
   - `grep -ril "execstack" testsuite/` → 零匹配
   - `grep -rn "execstack" Makefile.am src/Makefile.am testsuite/Makefile.am` → 零匹配
   - testsuite 中无任何脚本引用 execstack 工具

3. **execstack.c 源码无自检逻辑**：
   - 无 `self_test()` / `run_tests()` 等函数
   - 仅提供 `--version` / `--help` 和业务功能（设置/查询 PT_GNU_STACK 标志）

4. **prelink 本身无法编译**（需 GLOB_BRACE 等 glibc 独有特性，musl/OHOS 不支持），
   因此 prelink 的 testsuite 即使存在也无法在鸿蒙环境运行。

### 替代验证

由于上游无 execstack 专用测试，通过以下方式验证功能正确性：
- **test_package（本仓库）**：编译 test_execstack 程序，通过 `popen(execstack --version)` 实质调用 execstack 二进制
  验证其可执行、可加载共享库依赖（libelf/libargp/libobstack 等）、正常返回版本信息
- **W3 conan create**：test_execstack 测试 PASSED，exit_code=0

### 已知限制（非测试缺陷）
execstack 上游不支持 aarch64 ELF 文件（src/ 下无 arch-aarch64.c），
查询 aarch64 二进制时报 "architecture is not supported"。此为上游限制，不影响 x86 ELF 处理功能。

## 源码可达性（2026-08-30 CI 失败修复）

CI 首次构建（PR #7232）在 `conan create` 的 `source()` 阶段失败，根因有二：
1. CI 预下载步骤依赖 `curl`，但 CI worker 上**无 curl 命令**（`[Errno 2] No such file or directory: 'curl'`，3 次重试全失败）；
2. Conan 自身下载 `people.redhat.com` 在 CI worker 上**连接超时**（`connect timeout=30`，2 次重试全失败）。

prelink 是 Red Hat 个人主页（jakub）托管的冷门工具，主流镜像站不收录其 tarball——实测 USTC/清华/阿里云/FreeBSD distcache/Gentoo distfiles/sourceware/BLFS conglomeration/Savannah 全部 404 或超时。CI 镜像映射白名单（`ci/conan/build_and_test.sh` L935）仅对 github.com/ftp.gnu.org 等已知域名自动加镜像，`people.redhat.com` 不在白名单。

### 解决方案
conandata.yml 将 `url` 由单值改为**列表**（Conan 2.x `get()` 原生支持逐个尝试，网络错误时 fallback 到下一个 URL）：
1. 镜像源 `https://ftp.lysator.liu.se/pub/void-ppc-sources/prelink-20130503/prelink-20130503.tar.bz2`（首位，sha256 与官方源字节一致）；
2. 官方源 `https://people.redhat.com/jakub/prelink/prelink-20130503.tar.bz2`（保留兜底，偶发可达时仍用官方源）。

### file:// 方案废弃记录
最初曾尝试 `file:///storage/Users/currentUser/builds/execstack-20130503.tar.bz2` 本地兜底（参照 `archives/a/audit/4.1.2` 用法），但 CI 实测发现：CI worker 与本机**不共享** `/storage/Users/currentUser/builds/` 文件系统，`file://` 路径不存在时 Conan 抛出**未捕获的 FileNotFoundError**（非网络错误，不触发 fallback），导致构建直接崩溃。故改用 HTTPS 镜像方案。manifest.yaml 的 `source.url` 同步改为列表。
