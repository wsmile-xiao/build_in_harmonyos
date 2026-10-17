# robodoc 4.99.44 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.69 预生成 configure + automake 1.16 makefile.in）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（target: aarch64-unknown-linux-ohos）
- 平台: HarmonyOS（HongMeng Kernel 1.12.0）aarch64
- 状态: built

## 编译步骤

```bash
# 源码：官方 release 资产（含完整 makefile.in；git tag 归档缺 Source/makefile.in）
curl -LO https://github.com/gumpu/ROBODoc/releases/download/v4.99.44/robodoc-4.99.44.zip
unzip robodoc-4.99.44.zip && cd robodoc-4.99.44

# 应用补丁（config.guess / config.sub / configure / troff_generator.c）
patch -p1 < patches/0001-Source-troff_generator.c.patch
patch -p1 < patches/0002-config.guess.patch
patch -p1 < patches/0003-config.sub.patch
patch -p1 < patches/0004-configure.patch

./configure --prefix=$HOME/usr/local
make -j1
make install DESTDIR=$HOME/tmp/stage
```

真实构建记录（本机）：
- configure 日志: `$HOME/tmp/robodoc-logs/configure.log`（rc=0）
- make 日志: `$HOME/tmp/robodoc-logs/make.log`（rc=0）
- install 日志: `$HOME/tmp/robodoc-logs/install.log`（rc=0）
- 产物: `bin/robodoc`、`bin/robohdrs`、`share/man/man1/{robodoc,robohdrs}.1`、`share/doc/robodoc/*`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` / `config.guess: unable to guess system type` | 上游 config.guess(2018-02-24) 无 HarmonyOS 分支（`uname -s` 返回 `HarmonyOS`） | 补 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`；老式 config.guess 分支须 `echo ...; exit` 结尾，否则 fall through |
| 2 | `configure` 生成脚本报 `cannot find input file: 'Source/makefile.in'` | git tag 归档缺该文件（上游 .gitignore 忽略且未纳入版本控制） | 改用官方 release 资产 zip（`make dist-zip` 产出，含完整 makefile.in） |
| 3 | `config.status[754]: can't create ./confXXXXXX/subs1.awk: Permission denied` → `could not setup config files machinery` | HMDFS 新目录强制 setgid，`umask 077 && mktemp -d` 生成 2700 目录，属主亦无法写入 | configure 中两处 `umask 077` 改 `umask 022`（E129）；configure 内代码会写入生成的 config.status，一处修改同时生效 |
| 4 | `WARNING: 'automake-1.16' is missing` → make 失败 | 发布包内 `makefile.am` 与 `makefile.in` 时间戳相同，make 判定过期并尝试 automake maintainer 重建（OHOS 无 automake） | 构建时抬高 `makefile.in`/`config.h.in` 的 mtime 跳过重建（不改内容） |
| 5 | `troff_generator.c:33:10: fatal error: 'sys/unistd.h' file not found` | `<sys/unistd.h>` 为 SysV 遗留头，OHOS（clang/musl）不提供 | 改为标准 `<unistd.h>` |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| `0001-Source-troff_generator.c.patch` | `Source/troff_generator.c`：`#include <sys/unistd.h>` → `#include <unistd.h>` |
| `0002-config.guess.patch` | `config.guess`：新增 `*:HarmonyOS:*:*` 分支 → `aarch64-unknown-linux-ohos` |
| `0003-config.sub.patch` | `config.sub`：maybe_os 列表与 OS 列表新增 `linux-ohos` 组合 |
| `0004-configure.patch` | `configure`：临时目录创建处 `umask 077` → `umask 022` |

> 全部为可移植性修改，未引入平台宏（R8）；未使用 `--build/--host` 绕过平台探测（E007）。

## 依赖版本

无外部依赖（纯 C 标准库 + POSIX）。产品为命令行工具，非库。

## 上游测试入口清点（R51 三步法 · 第 1 步）

**结论：上游没有可执行的自动化测试套件。**

清点证据：
```bash
# 发布源码（本配方 sources.url）由 EXTRA_DIST 决定，不含 Test/ 目录：
unzip -l robodoc-4.99.44.zip | grep -c 'Test/'      # => 0
# 上游 git tag v4.99.44 源码树中的 Test/（未随发布包分发）：
ls -R Test/            # Build/ Functionality/ Performance/
wc -c Test/makefile Test/*/makefile                 # 全部 0 字节
grep -rn '^TESTS' --include=makefile.am .           # 无输出（make check 为空目标）
```

上游与测试相关的文件（均非自动化断言，详见 test_package/MANIFEST.yml）：
- `Test/Build/test_build.sh`：硬编码 `version=4.99.43` 与 `../../robodoc-4.99.43.tar.gz`，无对应 tarball，不可运行
- `Test/Functionality/generate_testcase.py`：仅随机生成测试源码树，不调用 robodoc、无断言
- `Test/Performance/makefile`、`Test/makefile`：空文件
- `Source/unittest.c`：未被 makefile 引用（不编译），含语法错误与硬编码 `/home/robodoc` 路径

**实跑结果**：`make check` rc=0、无输出（无 TESTS 注册）。

## 验证结果

```bash
$ robodoc --version
4.99.44
$ robodoc --config
ROBODoc version 4.99.44
Configuration:
  Compiled using ./configure; make;
  Compiler flags -fPIC -O2
  Compiled for aarch64-unknown-linux-ohos
  Prefix for excutable and configuration <prefix>
$ robodoc --src <sample-src> --doc <out> --multidoc --html --sections --toc   # rc=0，生成 HTML
$ robodoc --src <sample-src> --doc <out> --singledoc --ascii                  # rc=0，生成 ASCII
```

conan create（test_package）实测：`test.sh` 3/3 通过；`ohos_specific_test.sh` 7/7 通过，
合计 **10/10 PASS，0 FAIL，0 SKIP**（日志：`reports/conan-create.log`）。

## 注意事项

- 源码优先使用官方 release 资产；仓库 tag 归档可能缺 `.gitignore` 忽略的生成文件（本例 `Source/makefile.in`）。
- `configure` 为上游预生成脚本，补丁直接修改它（其内容会被复制进生成的 `config.status`），属 autotools 常规做法。
- release zip 不保存 POSIX 权限位，配方在 build() 中为 configure/辅助脚本补 `+x`。

### 对话 #1（2026-09-27）

- 在 HarmonyOS aarch64 本机完成 robodoc 4.99.44 原生适配：config.guess/config.sub
  平台识别（E007）、HMDFS umask 修复（E129）、`<sys/unistd.h>` 可移植性修复、
  automake maintainer 重建规避。
- 真实构建（configure/make/install 均 rc=0）、上游 `make check` 空目标核验、
  conan create（G0–G4 + L2/L4/L5）与 test_package 全部通过。
- 新增鸿蒙特有测试 `test_package/ohos_specific_test.sh`（7 断言）：AArch64/musl 原生
  ELF、`aarch64-unknown-linux-ohos` 三元组、HMDFS 上真实 HTML/ASCII 文档抽取、robohdrs。

---

**编译结束**: 2026-09-27 17:38
**最终状态**: built
