# slay 3.0.2 适配笔记

## 源码与环境
- 官方源码：Salsa Debian `debian/3.0.2` tag，tarball SHA256 `fc21c5f376760a52797308799528a42759877abef4d54c6305e1b853b0e1ca44`。
- 源码根目录只有无扩展名 `slay`（`#!/bin/sh`）与 `slay.8`；无 C/C++ 目标、Makefile 或 configure。构建方式为脚本复制打包；x86_64 runner 不交叉生成 aarch64 ELF，故 qemu 不适用。
- Debian `control` 写 `Depends: debconf | debconf-2.0`，但仅 `debian/config` 与 `debian/postinst` 引入 `/usr/share/debconf/confmodule`。交付 CLI 不安装 Debian 维护脚本，`slay` 本体不调用 debconf；Conan 无该依赖。W0 `conan download debconf/1.5.91 -r=ohpcd --only-recipe` 返回 `ERROR: error:system acceleration policy not enabled`，未据此虚构其发布状态。
- `lang_detect.detect_language` 对此树返回 `detected_language=other`、`build_system=none`、`source_stats=无源文件可统计`；检查 shebang 后确定是 POSIX sh 主程序。当前纯 shell 适配已允许，未调用会错误写入 `env_unsupported` 终态的 `lang-preflight`；已记录知识草稿。
- 工具初始化误识别 autotools，本包不存在 autotools 构建文件；生成配方已替换为无编译安装。

## 上游测试清点（R51）
- 官方 tag 中 `tests/` 目录 0；没有 Makefile/CTest/pytest 注册：0/0。`debian/` 下是配置、维护脚本和翻译而非测试；没有可运行的上游测试。未修改上游文件或测试。
- 从官方源码实跑 `sh slay --help` 返回 127 且打印 usage；`test_package` 使用缺目标、`--help`、`-clean --help` 三种输入验证同一条无目标 usage 安全分支（3/3），并固定 `SLAY_BUTTHEAD=off` 防止帮助文案受配置影响。故意不提供用户名：工具会尝试向目标用户所有进程发送信号，不允许真实破坏性测试。
- 动态 OHOS ELF / qemu 测试：不适用（仅 `#!/bin/sh` 脚本）。本地 x86 执行验证脚本逻辑；不能把它写成 aarch64 真机进程清理测试。

## 安装与产物
- Conan `source()` 从官方 Salsa tag 下载并按版本键校验 sha256；`package()` 只对包内副本修正 OHOS 的 shebang（`/system/bin/sh`）与 PATH（先查 `/system/bin:/data/service/hnp/bin`），将 `slay` 放入 `bin/`、手册放入 `share/man/man8/`、Debian copyright 和 Debian `/usr/share/common-licenses/GPL-2` 指定的完整 GPL-2 正文（随配方 `GPL-2.0.txt`）放入 `licenses/`；不执行 debhelper 或 debconf。Linux 包副本保持上游脚本不变；保留不同 OS 的 Conan package ID，避免跨平台脚本产物被错误共用。
- 运行时依赖 POSIX `sh`、`whoami`、`basename`、`tr`、`write`、`su`、`kill`、`grep`；上游写死 PATH 为 `/usr/sbin:/sbin:/usr/bin:/bin`，OHOS 包副本增加 `/system/bin:/data/service/hnp/bin`。实际杀进程功能仍依赖目标机具备这些命令与权限；未在本机/目标机实测破坏性分支。
- 不修改上游源码，不需要补丁；打包时适配脚本副本的 shebang/PATH（E165）；配方没有外部 Conan 依赖。
---

**编译结束**: 2026-09-24 18:50
**最终状态**: built
