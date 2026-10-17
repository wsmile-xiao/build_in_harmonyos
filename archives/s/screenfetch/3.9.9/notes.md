# screenfetch 3.9.9 适配笔记

## 软件概况

screenFetch 是一个纯 Bash 脚本工具，用于在截图中展示系统/主题信息。
上游仅发布单个自包含脚本 `screenfetch-dev` 和一份 man 页 `screenfetch.1`，
无 configure、无 Makefile、无 C 代码、无测试套件。

## 适配过程

### 源码
- 官方 tag 归档：`https://github.com/KittyKatt/screenFetch/archive/refs/tags/v3.9.9.tar.gz`
- sha256：`65ba578442a5b65c963417e18a78023a30c2c13a524e6e548809256798b9fb84`
- 解压后内容：`screenfetch-dev`（主脚本）、`screenfetch.1`（man 页）、`COPYING`（GPL-3.0）、`README.mkdn`、`CHANGELOG`、`TODO`、`update-manpage.sh`

### 安装方式
screenfetch 没有 Makefile，安装即文件拷贝：
1. `screenfetch-dev` → `bin/screenfetch`（沿用各发行版的命令名约定，与 `screenfetch.1` man 页一致），并 `chmod +x`
2. `screenfetch.1` → `share/man/man1/screenfetch.1`
3. `COPYING` → `share/licenses/screenfetch/`，`README.mkdn` → `share/doc/screenfetch/`

conanfile.py 的 `build()` 无需做任何事；`package()` 完成上述拷贝与改名。

## 平台兼容性
- Shebang 为 `#!/usr/bin/env bash`，不依赖 `/bin/bash`，OHOS 兼容
- 运行时仅需 Bash 4.0+ 与常见 coreutils（awk/sed/grep/date/cut 等），HarmonyOS PC 均自带
- 容器内实测：`bash 5.3.0(1)-release (aarch64-unknown-linux-ohos)`，`screenfetch --version` 输出 `screenFetch - Version 3.9.9`
- 注意：脚本顶层（line 201 附近）会无条件调用 `date`，PATH 缺 coreutils 时会在 stderr 报一条 `date: command not found`，但不影响 `--version`/`--help` 退出码（仍为 0）与 stdout 内容；test_package 已在 PATH 中并入工具目录规避此噪声

## 上游测试
- 上游无任何测试用例（无 tests 目录、无 test 框架、tar 内仅一个脚本 + man 页）
- 上游测试用例统计：0

## test_package
- `test_package/test.sh`：实质运行安装后的 `screenfetch` 命令
  - Test 1：`screenfetch --version` 输出含 `Version 3.9.9`
  - Test 2：`screenfetch --help` 输出含 `usage`
- 断言数：2

## 实跑环境
- 在 HarmonyOS aarch64 环境（构建容器，`uname -s`=Linux、hnp clang 为 Alpine musl、bash 5.3.0 aarch64-unknown-linux-ohos）实测 `conan create` + test_package 通过
- 本地实测与 CI 真实鸿蒙 worker 存在已知差异（见 PR 正文 `## 补充说明`）

---

**最终状态**: built

## 鸿蒙真机复测

- 日期：2026-07-19
- 环境：HarmonyOS HAD 206.1.0 真机（aarch64 musl，OHOS SDK clang 15.0.4）
- 结果：✅ 通过（conan create + test_package 真机原生执行）
