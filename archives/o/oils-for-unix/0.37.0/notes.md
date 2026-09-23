# oils-for-unix 0.37.0 适配笔记

## 上游基线

- 软件：oils-for-unix 0.37.0（Oils 项目的 C++ 版 Unix shell）
- 官网：https://oils.pub/ ，发行说明 https://oils.pub/release/0.37.0/
- 源码仓库：https://github.com/oils-for-unix/oils （旧名 oilshell/oil，无 git tags，发行物在 oils.pub 下载站）
- 源码：https://oils.pub/download/oils-for-unix-0.37.0.tar.gz
- SHA256：f4d41d20a0523dbcfbd4ba231f82edf25b08d4965d65bc71fcb56666d6743000（与官方发布页校验和一致）
- 许可证：Apache-2.0
- 语言：C++（cpp），38 个 .cc + 1 个 .c，主体占比 97%（lang-preflight 判定 cpp）

## 编译环境

- 构建系统：自定义（POSIX sh `./configure` + `_build/oils.sh` 编译驱动，非 autotools / 非 raw Makefile）
- 编译器：clang 15.0.4 / clang++ 15.0.4（target aarch64-unknown-linux-ohos）
- 依赖：无强制第三方依赖（仅 C++11 编译器 + libc/libc++）；GNU readline 可选，OHOS 未提供
- 状态：built

## 编译步骤

```bash
# 1. 特性检测（cc 在 OHOS 上不存在，需显式指定 C 编译器；禁用可选 readline）
./configure --prefix=<prefix> --cxx-for-configure=clang --without-readline

# 2. 编译 C++ shell（c++ 在 OHOS 上不存在，需显式指定 C++ 编译器）
_build/oils.sh --cxx clang++ --without-readline

# 3. 安装（上游默认安装 strip 后二进制，OHOS 上需安装未 strip 的二进制）
./install _bin/clang++-opt-sh/oils-for-unix
```

产物：`bin/oils-for-unix`（可执行）+ `bin/osh`、`bin/ysh`（符号链接）+ `share/man/man1/osh.1`（man page）。

## 原始 OHOS 失败与修复

### 失败 1：`cc` 与 `c++` 命令不存在

- **现象**：`./configure` 默认 `--cxx-for-configure=cc`，`_build/oils.sh` 默认 `--cxx cxx`（映射到 `c++`）；OHOS 环境无 `cc`/`c++` 符号链接，导致 feature test / 编译找不到编译器。
- **根因**：OHOS 工具链只提供 `/data/service/hnp/bin/clang` 与 `/data/service/hnp/bin/clang++`，无 `cc`/`c++` 别名。
- **修复**：configure 传 `--cxx-for-configure=clang`，build 传 `--cxx clang++`；配方中从 `tools.build:compiler_executables` 获取编译器。

### 失败 2：strip 后的二进制在 OHOS 上无法执行

- **现象**：`_bin/clang++-opt-sh/oils-for-unix`（未 strip）可正常运行；`oils-for-unix.stripped`（`strip` 重写后）执行报 `sh: ...: Operation not permitted`（EPERM）。
- **根因**：OHOS 平台 ELF 校验拒绝 `strip` 重写后的镜像（未 strip 的镜像带 `.note.ohos.ident` 等原始段，可正常 exec）。
- **修复**：打包未 strip 的 `oils-for-unix` 二进制（功能一致，可直接运行）。

### 失败 3：`install` 命令不在 PATH

- **现象**：`./install` 脚本调用 coreutils `install`，报 `install: inaccessible or not found`。
- **根因**：OHOS 上 `install` 位于 `/bin/install`，而默认 PATH 不含 `/bin`。
- **修复**：配方 `package()` 直接用 `copy()` 复制二进制并 `os.symlink` 建立 osh/ysh 链接，避免依赖 `install` 命令。

## 平台差异矩阵

| 项 | Linux (Debian/Ubuntu) | OHOS aarch64 |
|----|----------------------|--------------|
| `cc`/`c++` 别名 | 存在（gcc 提供） | 不存在，需显式 clang/clang++ |
| GNU readline | 可选可用 | 不可用，`--without-readline` |
| `strip` 后二进制执行 | 正常 | EPERM，需用未 strip 二进制 |
| coreutils `install` | /usr/bin/install | /bin/install（不在默认 PATH） |
| C++ stdlib | libstdc++ | libc++（libc++_shared.so） |

## 依赖版本

无 conan 依赖（`required: []`）。运行期依赖系统库 `libc.so`（musl）与 `libc++_shared.so`。

## 上游测试说明（R51）

- 发布 tarball 不含完整测试套件：无 `test/`、`spec/` 目录，无 `Makefile` / `make check` / `ctest` 目标（测试套件仅在 git 仓库中，且针对 dev 构建）。
- 构建验证采用上游 INSTALL.txt 的 smoke test 流程：`osh -c 'echo hi'`、`ysh -c 'echo hi'`、`osh -n configure` 等。
- test_package 中已实现 5 项真实断言（--version / osh echo / osh 算术 / ysh echo / ysh JSON）。

## 验证结果

```bash
$ _bin/clang++-opt-sh/oils-for-unix --version
Oils 0.37.0		https://oils.pub/

$ _bin/clang++-opt-sh/osh -c 'echo hi'
hi

$ _bin/clang++-opt-sh/ysh -c 'json write ({x: 42})'
{ "x": 42 }
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/oils-for-unix | 主二进制（未 strip，OHOS 可直接执行） |
| bin/osh | 符号链接 → oils-for-unix |
| bin/ysh | 符号链接 → oils-for-unix |
| share/man/man1/osh.1 | man page |

## 注意事项

- oils-for-unix 必须**在源码树内**构建（上游明确不支持 out-of-tree build），配方用 `chdir(self.source_folder)` 保证。
- 上游构建目录名由 `--cxx` 参数决定（`_bin/<cxx>-opt-sh`），配方传 `--cxx clang++` 使目录固定为 `_bin/clang++-opt-sh`。
---

**编译结束**: 2026-09-06 02:20
**最终状态**: built
