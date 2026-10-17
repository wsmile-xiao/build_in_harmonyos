# iucode-tool 2.3.1 适配笔记

## 编译环境

- 构建系统：Autotools (`configure.ac` + `Makefile.am`)
- 目标：HarmonyOS PC aarch64 / Conan `os=OHOS`, `arch=armv8`
- 编译器：clang 15 / llvm-ar / llvm-ranlib
- 源码：官方 GitLab `v2.3.1` archive
- 源码 SHA-256：`e24951098b5753293e43689bd8e0a61c4fd2e68870672d20bb89b093dfd8b255`
- 当前归档状态：built（Conan verify、W3 和归档收尾已完成；PR/平台发布未执行）

## 上游性质与功能边界

iucode-tool 是 GPL-2.0 的命令行工具，解析、校验、筛选和重新打包 Intel
IA32/x86_64 微码数据。上游实现包含 x86 `cpuid.h` 直接指令和 Linux cpuid
设备扫描；这些能力不适用于 HarmonyOS PC aarch64。本适配仅禁用硬件 CPUID
扫描，不伪造 Intel CPU 签名，不声明能够向 `/dev/cpu/microcode` 写入微码。
离线微码文件解析、筛选和输出仍由原始代码路径提供。

## W0/W1

- `argp-standalone/1.5.0` 已发布并通过 `conan download ... --only-recipe`。
- 构建工具 `automake/1.18`、`libtool/2.5.4` 已发布并通过 W0 检查。
- 从最新 `upstream/main` (`2e478fc4a2`) 创建 `feat/iucode-tool-2.3.1` 隔离 worktree。

## 源码修改

`patches/0001-ohos-arm64-disable-x86-cpuid.patch`：

1. 在 `iucode_tool.c` 引入 `<limits.h>`，使 OHOS 提供 `PATH_MAX` 与 `SSIZE_MAX`。
2. 仅在 Autoconf 检测到 `HAVE_CPUID_H` 时包含 x86-only `<cpuid.h>`。
3. 在没有 `HAVE_CPUID_H` 时让 `scan_system_processors()` 输出能力不可用并返回
   不改变筛选列表的成功回退；这样离线处理路径保持可用，硬件扫描不会被伪造。

recipe 仅接受 Conan `os=OHOS`，使用 `--disable-cpuid-device` 关闭 Linux cpuid
设备路径，并显式指定 `--build/--host=aarch64-unknown-linux-ohos`，避免 HMDFS
上 config.guess 的临时文件探测；不对原生 Linux 路径作错误兼容声明。源码无生成
`configure` 时，以已发布的 `automake/1.18` 与 `libtool/2.5.4` 自举。Autoconf 的 `pwd` 检查改用 shell 的 `PWD`，而 configure
临时目录放在 `/data/storage/el2/base/cache` 的工作区（只迁移临时文件，不迁移
Conan 构建树）。`argp-standalone/1.5.0` 作为 Conan 运行时构建依赖提供
`argp.h` 和 `libargp.a`。

## 手工诊断构建

GitLab archive 没有生成的 `configure`/`Makefile.in`；在诊断副本中运行：

```text
autoreconf -fi
./configure --prefix=/storage/Users/currentUser/usr/local --disable-cpuid-device
make -j1
make check
make install DESTDIR=...
```

诊断副本位于 `/data/storage/el2/base/cache/iucode-tool-2.3.1-work-diagnostic`，
仅用于定位 HMDFS/getcwd 与源码问题，不作为交付路径或通过证据替代 Conan clean build。

结果：

- configure：通过；识别 `aarch64-unknown-linux-ohos`。
- make：通过；仅有上游 `-Wcast-align`、`-Wsign-conversion` 和禁用 x86 路径的
  unused-function 警告，无错误。
- make check：退出 0，但没有执行任何测试命令；这是空 Automake check 目标，
  不能计为上游测试通过。
- install：通过；上游 `sbin_PROGRAMS` 在 Conan 的 AutotoolsToolchain 中映射为
  `bin/iucode_tool`，并安装 `share/man/man8/iucode_tool.8`。
- 实际命令：`--version`、`--scan-system`、`--list` 均退出 0；`--scan-system`
  明确输出 `direct CPUID scan unavailable on this architecture`。
- ELF：AArch64 PIE 动态可执行文件；正式 Conan verify 已重新构建并完成产物检查。

## 上游测试审计

官方 v2.3.1 源码包含 `COPYING`，但没有 `test/` 或 `tests/` 目录、没有测试框架
注册、没有 `TESTS`/`check_PROGRAMS` 测试程序。`make check` 是空目标，退出 0 但不
运行测试。因此 MANIFEST 明确 `upstream_tests_exist: false`，消费者测试单独运行
三条真实二进制命令，且 `--scan-system` 断言 arm64 fallback 文本，断言数为 3。

## 交付物

- 软件级 `README.md`、`manifest.yaml`、`commands.json`
- 版本级 Conan recipe、源码校验和、OHOS patch、manifest、notes
- `test_package/test.sh`、Conan test recipe 和 MANIFEST

## Conan verify 结果

`python3 scripts/ohc-run.py conan-verify iucode-tool 2.3.1` 已通过：G1、G2
(clean `conan create`)、G3、G4、L2、L4、L5 均 PASS。clean create 使用
`autoreconf -fi`，在 OHOS 6.0 aarch64 上编译并执行 test_package 的 3 条断言，
结果 `pass=3 fail=0`。完整日志为 `reports/conan-create.log`，汇总为
`reports/conan-verify-report.md`。

## 收尾结果

- `python3 scripts/ohc-run.py conan-verify iucode-tool 2.3.1`：G1、G2、G3、G4、L2、L4、L5 全部 PASS。
- `finish iucode-tool 2.3.1 built`：W3 本地 CI PASS；随后清理 Conan 缓存并重新运行 clean `conan create`，确认真实 from-source bootstrap/build/install 与消费者测试，再次通过。
- 归档打包产物已生成并完成 `--version` staging 验证；release 与 debug tarball 均由最终 OHOS aarch64 Conan 包 `iucodf0e575f53c2f8` 生成。
  - release SHA-256：`60120dff0d4a63ae225c83d98043b4baa2808d139c44e8531f78e011ae7c92cd`
  - debug SHA-256：`2d883b32025ea810170da9a9e7a3a4ac83fdd914910187284034493eaf84b50a`
- finish 的独立 legacy G0 configure 检查因未执行 Conan recipe 的运行时 `PWD/TMPDIR` 修复而报告 EXPECTED；不替代 Conan G2 结果，也未被记为 upstream test pass。
- W5 报告仓库既有知识条目字段缺失和大量草稿，另有 SUMMARY 生成器类型错误；这些是全仓工具问题，不是本包构建失败。
- `feedback/SKILL_FEEDBACK_2b168575.md` 已完成，结果协议保留 `partial`：尚未创建 PR、远程 CI 或平台发布声明。

## 对话记录

### 对话 #1
- 2026-09-26：主 Agent 根据官方 GitLab 来源、Conan clean create、test_package、W3 日志和归档检查完成本次适配与证据整理。

---

**编译结束**: 2026-09-26 13:05
**最终状态**: built
