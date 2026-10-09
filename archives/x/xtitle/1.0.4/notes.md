# xtitle 1.0.4 — HarmonyOS PC 适配记录

## 来源与构建

- 用户指定上游代码仓库：`https://salsa.debian.org/debian/xtitle.git`；本配方使用作者官网 `https://kinzler.com/me/xtitle/xtitle-1.0.4.tgz`（官网当前 HTML 明列 Download Version 1.0.4；SHA256 `cadddef1389ba1c5e1dc7dd861545a5fe11cb397a3f692cd63881671340fcc15`），而非 Debian 二次归档。作者版权和 `version=1.0.4` 与源码一致。
- 上游 `README` 指明脚本可手工安装。发布包含 `xtitle.sh`、`xtctl.sh`、`Imakefile`、手册和许可文件；**无 C/C++ 源、无需交叉编译或链接**。`Imakefile` 是可选 X11 安装配置，不能视为 Autotools `configure`；配方直接将两个未修改的 POSIX 脚本安装为 `bin/xtitle` 与 `bin/xtctl`，不需要 X11 开发库。
- 依赖：无 Conan 开发依赖；Debian 的 `debhelper` 仅服务 Debian 自己的打包，不是本软件运行/构建依赖。环境：Conan 2.29.1、aarch64-linux-ohos profile；脚本原生可由目标机 POSIX shell 解释执行，无 ELF 交叉产物；本机 `qemu-aarch64` 不适用于解释型脚本，故 **qemu 交付 ELF 实跑不适用**。
- `lang-preflight --lang other` 回报 `detected_language=other`（无可统计源文件）。这是旧 R47 将 Bash 一律视作辅助脚本的已知局限；当前任务已由用户明确批准纯 shell 可适配，故按实际无编译类型复核继续，而不虚称 C/C++。

## R51 上游测试清点与新增断言

| 项目 | 发现数 | 实跑通过 |
|---|---:|---:|
| 官方 tgz 内 `tests/` 目录 | 0 | 不适用 |
| `ctest`/`pytest` 注册测试 | 0 | 不适用 |
| `Imakefile` 中 `check`/`test` 目标 | 0 | 不适用 |
| 适配新增包消费测试 | 7 | 隔离安装实跑 7/7；`conan create` 结果以 W3 为准 |
| 鸿蒙特有测试（PC 终端会话） | 1 | 隔离安装实跑 1/1；反向验证：换成空壳 `xtitle` 后测试失败（rc=1） |

`test_package/test_xtitle.py` 实际运行包内两个命令，断言 `xtitle --version`、默认/仅标题/仅图标转义序列、`xtctl` 前景/背景/光标色转义序列。上游用例无修改，亦未给上游新增用例。

**鸿蒙特有测试（N=1）** `ohos_pc_terminal_session()`：模拟鸿蒙 PC 终端的使用条件——无 X11（环境中不设 `DISPLAY`）、`TERM=xterm-256color`、通过系统 shell `/system/bin/sh` 以参数方式启动包内 `xtitle`（避开 HMDFS 可执行位不可靠 / shebang 被拒，见 E087/E577），输出写入真实 PTY；断言 PTY 收到 `OSC 2`（标题）与 `OSC 1`（图标）序列及 `title =`/`icon  =` 回显，并要求退出码 0。缺少 `/system/bin/sh` 时测试直接失败，不会 skip 计为通过。

**证据边界**：本机为 x86 runner，`/system/bin/sh` 链接到宿主 `dash`，不是 OHOS 真机 shell；上述用例在此代理环境中实跑通过。脚本无 aarch64 ELF，`qemu-aarch64` 不适用；未在真实鸿蒙 PC 上肉眼观察窗口标题变化。

## 验证与问题

```text
sha256sum 官方 tarball: cadddef1389ba1c5e1dc7dd861545a5fe11cb397a3f692cd63881671340fcc15
install -m 755 xtitle.sh <staging>/bin/xtitle
install -m 755 xtctl.sh <staging>/bin/xtctl
python3 功能断言（真实 staging 二进制路径）: 7/7 passed
HarmonyOS PC terminal session (no DISPLAY, /system/bin/sh, PTY): 1/1 passed
负向对照（包内 xtitle 换成空壳）: 测试失败 rc=1
```

- 自动 `init-build` 把 `Imakefile` 错认为 Autotools，并产生 `TMPDIR` 缺失环境告警；实际包无需 configure/clang。`conan-init` 的原始自动模板误生成 Autotools C 库，已改成可复现纯 shell 工具配方；生成的 `test.c`/`CMakeLists.txt` 空壳不提交。
- 无上游补丁；不修改上游 shell 脚本。作者站原页面提供 HTTP 下载链接，实际同路径 HTTPS 可用，Conan 使用 HTTPS 与官方 SHA256。
- 历史归档：旧会话 `env_unsupported` 归档只含占位 `notes.md` 与生成 `manifest.yaml`，无可迁移构建经验；本轮从官方原版源码重新核验。暂停任务快照保留在仓库外，未捎带其 feedback/构建文件。
- `conan-verify` G1–G4 PASS（G2 确认 7/7 包消费测试）；`finish built` 中 W3 `setup.sh` + `build_and_test.sh` 通过（2026-09-25 复验：7/7 + 鸿蒙 PC 终端会话 1/1，合计 8/8）。G0 `./configure` 缺失是旧 Autotools 检测的假失败，step5b 为**全仓其他 E219/E253/E305 已存在缺字段**，step8 为 SUMMARY 自动生成 `str.append` 错误；不修其他包或正式知识库，按 W3 实际通过报告。`reports/test-report.md` 与实际 staging 验证记录已落本地门禁目录。
---

**编译结束**: 2026-09-25 06:15
**最终状态**: built
