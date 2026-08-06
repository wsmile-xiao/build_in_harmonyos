# alpine-chroot-install 0.14.0 适配笔记

## 编译环境
- 构建系统: makefile（仅 install 目标；单 POSIX shell 脚本，无编译步骤）
- 编译日期: 2026-08-05
- 编译器: N/A（纯 shell 脚本，clang 环境仅用于 conan 验证）
- 状态: built

## 编译步骤

1. 源码获取：GitHub 主站 tarball 下载超时，改用 codeload.github.com 成功
   `curl -sL -o alpine-chroot-install-0.14.0.tar.gz "https://codeload.github.com/alpinelinux/alpine-chroot-install/tar.gz/refs/tags/v0.14.0"`
2. 语法检查：`sh -n alpine-chroot-install` 通过（422 行单文件）
3. 安装验证：上游 `make install` 因 OHOS 无 coreutils `install` 命令失败（Error 127），
   等价实现为 `mkdir -p <dest>/usr/local/bin && cp alpine-chroot-install <dest>/usr/local/bin/ && chmod 755`
4. conan 配方：application 模式（无编译），package() 用 copy + chmod 打包 bin/ 与 licenses/
5. conan create / conan-verify / finish / W3 本地门禁全部通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 主站下载超时 | 外网到 github.com 主站不可达 | 改用 codeload.github.com，sha256 一致 |
| 2 | conan get() BadZipFile | codeload URL 无 .tar.gz 扩展名，conan 2.29 无法识别格式 | conandata.yml 增加 `filename: alpine-chroot-install-0.14.0.tar.gz` |
| 3 | make install Error 127 | OHOS 无 coreutils `install` 命令 | 配方 package() 用 copy + os.chmod 等价实现 |
| 4 | test_package 触发真实 chroot 下载 | OHOS `id -u` 报 bad uid，脚本 root 检查被绕过 | test_package 改为 sh -n 语法 + 打包完整性静态检查，不执行脚本 |

## 源码修改

无（0 补丁，纯脚本项目无源码修改）

## 依赖版本

- 无外部依赖（纯 POSIX shell，运行时依赖 /bin/sh）
- conan 2.29.1 / clang 15.0.4（仅验证环境）

## 验证结果

```bash
sh -n alpine-chroot-install          # 语法检查通过
conan create .                       # 通过（test_package: PASS）
ohc-run.py conan-verify ...          # G1-G4 + L2/L4/L5 全 PASS
ohc-run.py finish ... built          # EXIT_CODE 0
# 非 root 下脚本按预期快速失败: ERROR: This script must be run as root!
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/alpine-chroot-install | 21 KB | 主脚本（打包进 conan 包） |
| packaging/alpine-chroot-install-0.14.0-ohos-aarch64.tar.gz | 26 KB | 本地打包产物（不入 PR） |

## 注意事项

- 脚本运行需要 root + chroot/binfmt 内核能力（鸿蒙未实现），只能打包注册，实际安装 Alpine 无法在本机验证
- 上游测试入口：`.github/workflows/ci.yml`（v0.14.0 真实存在），4 架构矩阵（x86_64/aarch64/armv7/ppc64le）× 9 项断言（安装/enter-chroot uname/架构匹配/env/用户env/sudo用户env/printf/destroy/destroy--remove）；OHOS 上 0/9 可运行（依赖 root+chroot+网络），宿主侧仅基础命令等价验证
- 新增测试：test_package/test_smoke.sh 静态冒烟（5 断言：脚本存在/可执行/sh -n/shebang无NUL/LICENSE），独立于上游断言
- 运行时需外网访问 dl-cdn.alpinelinux.org 拉取 apk 包

## 第 5 轮上游 CI 取证（2026-08-05）

**上游测试入口核验**：`alpine-chroot-install-0.14.0/.github/workflows/ci.yml` 真实存在（tarball 内确认）。
- 触发：`on: [pull_request, push]`
- 矩阵架构：x86_64 / aarch64 / armv7 / ppc64le（runs-on: ubuntu-20.04）
- 9 项断言（按 ci.yml run 步骤）：
  1. `sudo ./alpine-chroot-install -a <arch>` — 安装 Alpine chroot（依赖 root + chroot/binfmt 内核能力 + apk 网络下载）
  2. `/alpine/enter-chroot uname -a`
  3. `[[ "$(/alpine/enter-chroot uname -m)" == <arch>* ]]`
  4. `/alpine/enter-chroot env`
  5. `/alpine/enter-chroot -u $USER env`
  6. `sudo /alpine/enter-chroot -u $USER env`
  7. `test "$(/alpine/enter-chroot printf %s! 'Hello, world')" = 'Hello, world!'`
  8. `/alpine/destroy`
  9. `/alpine/destroy --remove; ! test -d /alpine`

**OHOS 执行状态：0/9 blocked**（首个真实阻塞为断言 1）：
- `sudo ./alpine-chroot-install -a x86_64` → `open /dev/tty for write failed`（exit=1）；非 root 直跑 → `ERROR: This script must be run as root!`（exit=1）
- `chroot` 命令不可用（`sh: chroot: inaccessible or not found`）——鸿蒙未实现 chroot 内核能力
- 断言 2-9 全部依赖断言 1 生成的 /alpine chroot 环境，级联 blocked
- 宿主侧等价（仅基础命令，不等价于 chroot 内行为）：`uname -a`（HongMeng Kernel aarch64）、`uname -m`（aarch64）、`env`、`printf %s! 'Hello, world'` 均可用

**更正结论**：此前"无 CI workflow、上游 0/0"陈述不实，已更正为"上游 CI 4 架构 × 9 断言，OHOS 0/9 blocked，新增消费者静态 smoke test 1/1"。

**pipefail/R25 处理**：OHOS `/system/bin/sh` 实测支持 `set -o pipefail`（exit=0）；test_smoke.sh 已改为 `set -euo pipefail`，实测管道中间失败（head 读不存在文件）传播 exit=1，不被静默吞掉；正常路径 5 断言全 PASS。

## 第 6 轮 Linux 上游 CI 证据更正（2026-08-06）

**分析端独立 Linux 实测**（Ubuntu 22.04 x86_64 + QEMU/binfmt 环境，官方 v0.14.0 归档，未改上游源码；仅对安装器公开的 `APK_TOOLS_URI` 使用已校验离线 apk.static 2.12.10）：

| 架构 | Alpine 分支 | 结果 |
|------|-------------|------|
| x86_64 | latest-stable | 9/9 PASS |
| aarch64 | latest-stable | 9/9 PASS |
| armv7 | latest-stable | 9/9 PASS |
| ppc64le | v3.16（同期） | 9/9 PASS |
| ppc64le | latest-stable (v3.24) | 0/9 blocked |

**ppc64le latest-stable 首错**：ppc64le apk 3.0.7 无法读取旧 apk.static 2.12.10 初始化的数据库。QEMU 与 ppc64le apk 二进制均可启动，属上游随时间漂移的版本兼容边界，非适配缺陷。

**分层测试统计（更正后）**：
- 上游 workflow：4 架构 × 9 断言（`on: [pull_request, push]`，runs-on ubuntu-20.04）
- Linux 实测：x86_64 / aarch64 / armv7 当前环境 9/9 PASS；ppc64le 同期 v3.16 9/9 PASS；ppc64le 当前 latest-stable 因 apk 版本兼容边界未进入断言（0/9 blocked）
- OHOS：0/9 blocked（root/chroot/binfmt 内核能力缺失，鸿蒙未实现）
- 不得将历史 v3.16 结果伪称为当前 workflow latest-stable 的 4/4 绿灯
- 新增消费者静态 smoke test：1/1（5 断言，独立统计）

**MANIFEST.yml 已同步**：`upstream_tests[0].result_linux` 记录 Linux 分层结果，`status_on_ohos` 记录 OHOS 0/9 blocked。
---

**编译结束**: 2026-08-06 07:54
**最终状态**: built
