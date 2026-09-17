# libotf 0.9.16 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-13
- 编译器: clang / clang++（HNP 工具链，aarch64-linux-ohos）
- 目标平台: HarmonyOS PC / OpenHarmony aarch64（`os=OHOS`）
- Conan: 2.29.1（社区 OHOS 适配版）；profile `ci/conan/profiles/ohos-aarch64`
- 依赖: freetype/2.14.3（制品仓已发布，W0 预检通过）
- 状态: published

## 编译步骤
1. 源码: `https://download.savannah.nongnu.org/releases/m17n/libotf-0.9.16.tar.gz`
   （sha256 `68db0ca3cda2d46a663a92ec26e6eb5adc392ea5191bcda74268f0aefa78066b`）。
   上游发布包含预生成 `configure`，**不需要也不应**重新 autoreconf：本机
   `automake`/`aclocal` 不可用，且 `configure.ac` 比 `aclocal.m4` 新会触发
   上游损坏的 `aclocal-1.15` 规则（已通过保留 tarball 原始 mtime 规避）。
2. `./configure --prefix=$DEFAULT_PREFIX` —— 唯一参数；freetype 的头文件与
   链接参数经 `PKG_CONFIG_PATH` 由 pkg-config 探得（补丁 0003）。
3. `make -j1`（HMDFS 上 jobserver FIFO 不可靠，沿用仓库 559 个先例的 `-j1`）。
4. `make install DESTDIR=<staging>`。
5. Conan 侧：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同一 profile> --build=missing`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 报 `unknown`，交叉编译三元组无法确定 | 上游 2014 年版 `config.guess` 没有 HarmonyOS 分支 | 补丁 0001 增加 `HarmonyOS` → `aarch64-unknown-linux-ohos` 判定 |
| 2 | `config.sub` 拒绝 `aarch64-unknown-linux-ohos` | 上游 `config.sub` 的 `-linux*` 归一化分支排在前面，把 `linux-ohos` 改写成 `linux-gnu` | 补丁 0002 在 `-linux*)` 归一化**之前**插入 ohos 分支 |
| 3 | `configure` 静默 `HAVE_FREETYPE=no`，`FT_Load_Sfnt_Table` 等符号未定义 | FreeType 2.10 起移除 `freetype-config`；上游探测失败时**不报错**，只是把 `HAVE_FREETYPE` 置 no（E572） | 补丁 0003 改为 `pkg-config` 回退（先 `freetype2`、后 Conan `PkgConfigDeps` 的 `freetype`），并保证 `-lfreetype` 进入 `LIBS`/链接行 |
| 4 | `config.status` 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | autotools 以 `umask 077` 创建临时目录，HMDFS 下权限为 2700，目录不可写（E110/E011） | 补丁 0003 同一文件内把 `umask 077` 改为 `umask 022` |
| 5 | VPATH（out-of-tree）构建时示例程序 `fatal error: 'otf.h' file not found` | `example/Makefile.in` 只给了 `-I$(top_builddir)/src`；in-source 构建下 builddir==srcdir 才恰好可用 | 补丁 0004 补 `-I$(top_srcdir)/src` |
| 6 | `conan create` 应用补丁失败，前一轮本地 `patch` 却成功 | Conan 的补丁器 `patch-ng` 严格按 hunk 行号定位，**不做** GNU patch 式上下文偏移搜索；补丁 0003 先把 `configure` 改动了 +16 行，补丁 0004 的 umask hunk 随即整块失配（E577） | 把同一目标文件（`configure`）的两处改动**合并为单个补丁** `0003-configure.patch`，hunk 行号统一基于原始文件 |

## 源码修改

| 补丁 | 文件 | 内容 |
|---|---|---|
| `0001-config.guess.patch` | `config.guess` | 识别 HarmonyOS + aarch64，输出 `aarch64-unknown-linux-ohos` |
| `0002-config.sub.patch` | `config.sub` | 接受 `aarch64-unknown-linux-ohos`（先于 `-linux*` 归一化命中） |
| `0003-configure.patch` | `configure` | ① freetype 探测回退 pkg-config（`freetype2`/`freetype`）+ 保证 `-lfreetype` 进链接行；② 临时目录 `umask 077` → `022` |
| `0004-example-Makefile.in.patch` | `example/Makefile.in` | 补 `-I$(top_srcdir)/src`，修复 VPATH 构建下 `<otf.h>` 找不到 |

补丁均只改**预生成/构建脚本与 Makefile.in**，未触碰 `configure.ac`/`Makefile.am`
源（本机 automake 不可用，无法重新生成）；未在补丁中引入任何平台宏判断。

## 依赖版本
- `freetype/2.14.3`：`otf.h` 是公开头文件且内部 `#include <ft2build.h>` /
  `FT_FREETYPE_H`，故 recipe 声明 `transitive_headers` + `transitive_libs`，
  消费者 `requires = "libotf/0.9.16"` 即可直接包含 `otf.h` 并链接 `-lfreetype`，
  无需手工拼 freetype 头文件/库路径。

## 验证结果

```bash
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
...
libotf/0.9.16: test.sh: 用例 5 个, 失败 0 个
libotf/0.9.16: ALL TESTS PASSED (test_ohos.sh: 1 用例 / 9 断言)
libotf/0.9.16: libotf: 单元 1 + 集成 4 + 鸿蒙特有 1 用例全部通过
libotf/0.9.16: Package '<cache>/p/b/libotf...' created
```

- 用例: 6（单元 1 + 集成 4 + 鸿蒙特有 1）全部通过，0 失败
- 断言: 30（单元 17 + 集成 4 + 鸿蒙特有 9）
- 实测样本: `otfdump` 转储 30528 行（含 GSUB）；`otflist` 260 行；
  `otftobdf` 输出 12204 字节 BDF / `CHARS 389`；损坏字体负向 rc=1 且未被信号杀死
- 详细数据见 `reports/test-report.md`

## 注意事项
- **上游没有测试套件**（无 `tests/` 目录、无 `check` 目标、无测试框架注册）；
  `example/` 下 4 个程序是使用示例，其中 `otfdump`/`otflist`/`otftobdf` 随
  `make install` 安装，`otfview` 需要 X11（`if !X11_UNAVAILABLE`）在 OHOS 下
  不构建。适配测试以"端到端驱动这 3 个上游工具 + 消费者 API 单测 + 鸿蒙特有
  检查"覆盖，详见 `reports/test-report.md`。
- `OTF_check_table(otf, name)` 的返回口径与常见 errno 风格**相反**：
  **0 = 表存在**，**-1 = 不存在**（并在 `OTF_error` 置位）。
- 库产物为 `libotf.so.1`（SONAME `libotf.so.1`），动态链接 freetype；
  `bin/` 下 4 个工具（含 `libotf-config`）按 R38 在软件级目录声明 `commands.json`。
- 本机 `/system/bin/sh` 为 MIRBSD KSH，测试脚本按 POSIX sh 编写（未使用 bash 语法）。

## 对话记录

### 对话 #1 [2026-09-13]

- 问题: 上游 2014 年版 `config.guess` 在 HarmonyOS 上输出 `unknown`，`config.sub`
  又拒绝 `aarch64-unknown-linux-ohos`，交叉编译三元组无法确定
- 操作: 补丁 0001 给 `config.guess` 增加 `HarmonyOS` 分支；补丁 0002 在
  `config.sub` 的 `-linux*)` 归一化分支**之前**插入 ohos 分支
- 结果: `guess=[aarch64-unknown-linux-ohos]`，configure 正常推进，无回归

### 对话 #2 [2026-09-13]

- 问题: `configure` 静默把 `HAVE_FREETYPE` 置 no，`libotf.so` 链接期
  `undefined reference to FT_Load_Sfnt_Table`
- 操作: 定位为 FreeType 2.10 起移除 `freetype-config`，而上游探测失败不报错
  （E572）；参照仓库 cube2font 的 `pkg-config` 回退写法改 `configure`
- 结果: 同时探测 `freetype2.pc`（上游惯用名）与 Conan `PkgConfigDeps` 生成的
  `freetype.pc`，`-lfreetype` 进入 `LIBS`，`libotf.so` 正确链接 `libfreetype.so.6`

### 对话 #3 [2026-09-13]

- 问题: `config.status` 报 `can't create ./confXXXXXX/subs1.awk: Permission denied`
- 操作: 复现确认 autotools 以 `umask 077` 创建临时目录，HMDFS 下权限为 2700
  不可写（E110/E011）；沿仓库 958 个先例的 configure 补丁口径
- 结果: 补丁把 `umask 077` 改为 `umask 022`，`config.status` 正常生成

### 对话 #4 [2026-09-13]

- 问题: out-of-tree（VPATH）构建示例程序时报 `fatal error: 'otf.h' file not found`
- 操作: 定位 `example/Makefile.in` 只给 `-I$(top_builddir)/src`，in-source 构建
  下 builddir==srcdir 才恰好可用；Conan 构建为 VPATH，故必然失败
- 结果: 补丁 0004 补 `-I$(top_srcdir)/src`，`example/` 下 3 个工具构建通过

### 对话 #5 [2026-09-13]

- 问题: 本地 GNU `patch` 应用成功的补丁，`conan create` 里 patch-ng 却整块失配
- 操作: 对比确认 patch-ng **不做** GNU patch 式上下文偏移搜索，只按 hunk 行号
  定位；补丁 0003 先改动 `configure` 使后续 hunk 行号整体偏移
- 结果: 把同一目标文件的两处改动合并为单个 `0003-configure.patch`，行号统一
  基于原始文件；沉淀为知识草稿 E577

### 对话 #6 [2026-09-13]

- 问题: `finish` step [1/10] `refresh-patch --auto` 从 work 目录重新生成补丁，
  把只存在于归档的手写补丁 0004 删除，conandata 引用悬空导致 W3 失败
- 操作: 改为让 work 目录成为唯一事实源——把 VPATH 修改同步进
  `example/Makefile.in` 后再跑 `refresh-patch --auto`，并同步 conandata/manifest
  里被重命名的补丁文件名
- 结果: 4 个补丁全量重生成（含 `0004-example-Makefile.in.patch`），W3 `conan create`
  通过
---

**编译结束**: 2026-09-14 00:38
**最终状态**: published
