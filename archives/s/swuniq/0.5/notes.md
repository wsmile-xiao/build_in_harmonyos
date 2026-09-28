# swuniq 0.5 适配笔记

## 来源与依赖
- 上游：`https://github.com/mterron/swuniq.git`，标签 `v0.5`（commit `59521c1ba7cd02b6532bdec1d48cad95be599753`）。官方源码归档：`https://codeload.github.com/mterron/swuniq/tar.gz/refs/tags/v0.5`，SHA256 `82ff7f406e6581b2e1edce12d519aebfb3bbf372acb5ac13c88d370cd26403b2`。
- 本标签 Git tree 的 `utarray.h` / `utringbuffer.h` / `xxhash.h` / `xxh3.h` 均为普通文件（`100644`），**没有 gitlink/submodule**；主线子模块结构不可直接套用到旧 tag。没有 Conan 依赖，只有 OHOS libc。
- 构建系统：单文件 C + Makefile；x86_64 runner、Conan 2.29.1、OHOS aarch64 clang，`qemu-aarch64`/binfmt；2026-09-25。状态：built（尚未发布）。

## 编译与上游测试清点（R51）
- 上游源码无 `tests/`（目录数 0），无 CTest/pytest 注册（0），`Makefile:check` 仅有 **1 项**：重复两次 1..10、`-w 10` 时输出 10 行；`Makefile` 为可复核的上游测试声明，`test_package/MANIFEST.yml` 如实登记。无修改上游测试源。
- 探索命令：`aarch64-unknown-linux-ohos-clang -O2 -static swuniq.c -o out/swuniq`；`cd /root/tmp/builds/swuniq-0.5.work && make check` → `Test suite result [SUCCESS] exit 0`，**1/1**。本机 binfmt 提供 OHOS 静态 aarch64 实跑（不是 skip）。
- 同源消费者交互：`printf 'a\nb\na\na\nc\na\n' | qemu-aarch64 out/swuniq -w 2` → `a\nb\nc\na\n`，diff 比较一致。

## Conan 交付与鸿蒙特有消费者测试（rule12）
- 配方从官方固定 tag 下载并校验 SHA256，用 profile `tools.build:compiler_executables["c"]` 指定编译器，显式 `-static` 避免 x86 runner 缺 OHOS 动态 loader；产物为 `bin/swuniq` CLI，软件级 `commands.json` 声明。静态产物本身是交付产物，非动态包的替代性验证副本。
- `test_package/test.c` 的 **鸿蒙特有用例 1 项**：读被测包 ELF header 验证 `EM_AARCH64`，经 OHOS libc 的 `pipe/fork/exec` 调用真实打包工具；子断言 `-w 2` 输出 `a,b,c,a` 和默认窗口输出 `a,b,c`。源码与命令见 `test_package/test.c`、`test_package/conanfile.py` 和 `reports/conan-create.log` 的 `PASS (2/2)`；同一消费者用例包含两项窗口行为断言，不能另算上游用例。
- Conan 验证：`CONAN_HOME=/data/harmony-compact/.conan2-ohos python3 scripts/ohc-run.py conan-verify swuniq 0.5` → G1/G2/G3 PASS，消费者 **2/2**，aarch64 包实跑通过。

## 问题和知识复用
- 错误：`get()` 从官方 codeload URL 下载后 `BadZipFile: File is not a zip file`。根因已有知识 `E483`（并有 `E276/E392`），URL 末段 `v0.5` 无压缩格式后缀；在 `conandata.yml` 给 `filename: swuniq-0.5.tar.gz` 后通过。自动引擎错命中 `E540`（与本错误无关的 PATH 问题），本次未重复造 BadZipFile 草稿。
- 新经验 `E545-draft-0086`：`init-build --url` 传 Git 仓库 `.git` 地址被当 tarball 下载且超时；改用按标签固定的官方 tar.gz，并先核对指定 tag 是否含 gitlink，避免误用主线 submodule 状态。
- W3 首跑被 `L1e` 拦截：`[fail] L1e: test passed WITHOUT package artifacts`。正向 create 已 `PASS (2/2)`；根因是 L1e 用单 profile `conan test`，`can_run(self)` 变假，`test()` 静默跳过返回 0。改为按 `platform.machine()` 判断：aarch64 直接跑，x86 显式 `qemu-aarch64` 跑测试程序并用 qemu exec 被测 CLI，两者都没有则 `ConanInvalidConfiguration` 失败。沉淀草稿 `E550-draft-1C7E`（查重最近 `E428`，根因不同）。
- 上游源码无补丁、无人工修改；`conan-init` 误识别为 autotools 导致自动骨架不适用于 Makefile CLI，已经按实际情况重写配方和测试。
---

**编译结束**: 2026-09-25 10:41
**最终状态**: built
