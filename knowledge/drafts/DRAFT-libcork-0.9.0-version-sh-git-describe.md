# DRAFT-libcork-0.9.0-version-sh-git-describe

## 问题 (Problem)

libcork 0.9.0（CMake 项目）在无 .git 的源码包（conan get 拉 tag tarball）中
配置时 CMake 报 `Cannot determine version number`（execute_process 返回 126）：
`version.sh` shebang 为 `#!/bin/bash`，而 OHOS 环境 `/bin/bash` 不存在
（bash 实际在 `/data/service/hnp/bin/bash`），脚本根本无法执行；
即使修正 shebang，脚本 `version=$(git describe)` 在无 .git 时失败、
`if [ -n ${version} ]` 因未加引号恒真，版本号会写成空串。

## 根因 (Root Cause)

1. `version.sh` shebang 硬编码 `/bin/bash`，嵌入/精简环境（OHOS、busybox）
   没有该路径（bash 仅存在于工具链目录，不在 /bin 下），直接 exec 126。
2. 版本探测依赖 `git describe`，发行 tarball / conan 源码包无 .git，探测必然失败。
3. 未加引号的 `[ -n ${version} ]` 在空变量时判断为真（测试的是 `-n` 字面串），
   上游脚本既不会报错也不会正确回退，版本号损坏而不自知。

## 方案 (Solution)

对 `version.sh` 打 portability 补丁（固化为
`archives/l/libcork/0.9.0/patches/0001-version.sh.patch`）：

- shebang 改 `#!/usr/bin/env bash`（PATH 可寻址）或 `#!/bin/sh`。
- `if [ -n ${version} ]` → `if [ -n "${version}" ]`；`-z` 同样加引号。
- `git describe 2>/dev/null || true` 静默失败后正确走 `RELEASE-VERSION` 回退。
- 配方 `source()` 显式写入 `RELEASE-VERSION` 文件（内容=版本号），
  使无 .git 场景有回退依据（与上游 make-dist.sh 行为一致）。

## 验证 (Verification)

- `bash version.sh`（无 .git、无 RELEASE-VERSION 初始态）→ 输出 `0.9.0`（exit 0）。
- conan create（OHOS aarch64 profile，4 补丁全应用）→ 通过，G2 产物完整。
- 上游测试 45 check + 29 cram = 74/74 通过；test_package 消费者验证通过。

## 适用边界 (Applicability / Scope)

- 适用：任何用 `git describe` 版本脚本（version.sh/version-gen.sh 等）+ CMake/
  autotools 构建、并以源码包/制品形式分发的项目（libcork、同类 RedJack 系等）；
  OHOS/嵌入式无 `/bin/bash` 环境尤其相关。
- 不适用：git clone 直接构建（有 .git，git describe 可用）；已有 RELEASE-VERSION
  发行包的官方 tarball（make-dist 已生成）。

## 查重差异

- 与 E157（jpeg-version.sh 需 cpp 预处理检测 JPEG 版本）场景不同。
- 与 E104（version_script.ver 链接脚本缺失）无关。
- 与 DRAFT-c-ares（config.guess/config.sub 平台识别 + umask）不同域。