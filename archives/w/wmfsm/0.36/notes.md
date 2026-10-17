# wmfsm 0.36 适配笔记

## 编译环境

- 构建系统：Autotools
- 编译日期：2026-09-28
- 目标环境：HarmonyOS PC 6.0，aarch64 / Conan `OHOS/armv8`
- 编译器：Clang 15
- Conan：2.29.1
- 状态：built（已验证，未发布）

## 编译步骤

在目标设备上使用仓库 profile 执行：

```sh
conan create archives/w/wmfsm/0.36 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方从官方 0.36 源码包校验 SHA256，依次应用两个补丁，运行 `autoreconf -i`、Autotools configure、`make -j1`、`make -j1 check`，再安装并运行 Conan `test_package`。上游没有注册测试，`make check` 成功但不执行测试用例。

干净 CI 镜像预装 autoconf 但没有 `aclocal`，因此配方声明 `automake/1.18` 为构建工具依赖。上游 `config.guess` 也无法识别设备的 HarmonyOS `uname` 输出，配方显式指定 `aarch64-unknown-linux-ohos` build/host triplet。
Buildbot #63504 在 HMDFS 构建目录中报告 `config.status` 无法创建 `confg.../subs1.awk`（Permission denied）。Autoconf 生成的 `configure` 含有 `umask 077`，配方在 `autoreconf -i` 后将这些临时目录掩码归一为 `022`，针对该 clean worker 报错增加规避。真机 W3 日志确认两个 marker 均已替换，worker 端仍需由推送后的 Buildbot 结果最终确认。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备没有可读的 `/etc/mtab` | 上游只读取 Linux 的 mtab 文件 | 保留 mtab 优先逻辑，打开失败后读取 `/proc/mounts`；设备端消费者测试强制 mtab 返回 ENOENT，并在应用开始挂载扫描后观察到真实 `statfs()` 成功 |
| 2 | Conan 的独立构建目录找不到 XPM | 上游 configure 将 `wmfsm/...` 按当前目录解析 | 通过 `${srcdir}` 定位 XPM，并在源目录更新链接 |
| 3 | HarmonyOS HNP `CONFIG_SHELL` 在 HMDFS 构建目录可能遇到 `getcwd()` 失败 | profile 指定的 shell 在该路径下不适用 | 配方生成 configure 参数后在执行 configure 时 unset `CONFIG_SHELL`，并传入依赖库目录供 Autoconf 链接探测 |
| 4 | CI `config.status` 创建 `subs1.awk` 时 Permission denied | Autoconf 使用 `umask 077` 创建临时目录，Buildbot HMDFS worker 无法在该目录继续写入 | `autoreconf -i` 后把生成的 `configure` 中 `umask 077` 改为 `umask 022`，并验证 marker 存在 |

## 源码修改

- `patches/0001-wmfsm-wmfsm.c.patch`：在 `/etc/mtab` 打开失败时回退到 `/proc/mounts`，不使用平台宏。
- `patches/0002-configure.ac.patch`：使 XPM 检查和链接适用于 Autotools out-of-source 构建。

## 依赖版本

- `libdockapp/0.7.3`
- `libx11/6.4.0`
- `libxext/6.4.0`
- `libxpm/3.5.17`

## 验证结果

- HarmonyOS AArch64 真机 Conan 构建通过；Conan consumer test 共 3/3 项功能检查通过。
- 仓库本地 CI：1/1 包成功；L0、L1、L4、L5 通过。L1 显示上游检查和 test_package 已执行；上游测试数为 0，test_package 有效消费者行为检查为 3 项、3 项通过。平台与 ELF 信息仅作为运行前置条件，不计作消费者功能测试。
- `test_package` 在 HarmonyOS 真机检查 `--version`、`--help`，并强制 `/etc/mtab` 不可用，验证程序读取真实 `/proc/mounts` 后，对解析得到的挂载点执行成功的真实 `statfs()` 调用。
- CI 的附加 L2 直接执行包内二进制时报告 version/help 失败并标记为 skip。用相同的无 `LD_LIBRARY_PATH` 方式复现时，设备动态加载器提示缺少 `libdockapp.so.3`、`libXpm.so.4` 等 Conan 依赖；CI 该步骤没有激活 Conan `VirtualRunEnv`。同两个 CLI 入口在 Conan 消费测试环境中均通过。
- 设备没有可用的 `DISPLAY`，未验证 X11 dock 窗口渲染；图形适配仍需在提供 X11 服务的 HarmonyOS PC 环境人工确认，不能据此宣称窗口渲染已完成适配。
- `.ci-result.json` 由设备端 `finish` 自动生成；其 `log_sha256` 与归档中的 `reports/w3-local-ci.log` 一致。W3 原始日志保留在该路径供本地验证复核；Conan Verify 的结论记于本笔记，临时报告不纳入源码归档。

### 流程备注

W3 阻塞门禁已通过，但本次完整 `finish` 返回部分完成：G0 干净构建步骤在验证镜像中找不到原始 tarball；旧式 finalize 检查仍要求 `packaging/`、release/debug tar.gz；W5 报告仓库现有知识条目 E219、E253、E305 有字段缺失（`graph validate` 本身通过）；submit readiness 还要求 `reports/test-report.md`、`packaging/` 与 `.staging-verified`。流程脚本还在独立验证副本生成 `SUMMARY.md`，因此该副本的 W2 原子性检查提示了框架文件；这不是 wmfsm 包变更，未复制或纳入本次 PR。上述工作流资料缺失不影响已通过的源码构建、Conan Verify 和 W3 本地 CI。此次只保留归档规范要求的 Conan 配方与验证证据，没有生成旧式二进制压缩包，也没有修改知识库或框架文件。

## 验收记录

### 对话 #1 — 2026-09-28

- 上游未打补丁时，设备端行为测试以 `Can't open /etc/mtab for reading` 失败；应用挂载回退补丁后，版本、帮助、procfs 挂载解析并成功 `statfs()` 三项运行时检查通过。
- OHOS/armv8 与 AArch64 ELF 检查仅是消费者测试运行前置条件，不计入功能测试数。
- 该版本已构建并验证，尚未上传到 Conan 制品仓。

### 对话 #2 — 2026-09-28

- 外部 Buildbot #63504 在 `config.status` 的 HMDFS 临时目录创建阶段失败，提示无法创建 `subs1.awk`。配方加入 umask 归一化。
- HarmonyOS AArch64 真机以独立、干净的 Conan home 在 `.cache` 下重新构建，并通过 Conan consumer test 3/3。真机上的干净构建没有复现 Buildbot 的 HMDFS 权限错误；修复仍保留对该 CI 报错的针对性规避。
