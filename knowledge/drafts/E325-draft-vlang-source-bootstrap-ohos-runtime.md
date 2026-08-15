# E325 草稿：Vlang 自举编译器的固定 bootstrap 源与 OHOS 运行时包装

> 结构化数据：`knowledge/drafts/E325-draft-vlang-source-bootstrap-ohos-runtime.kv`
> 状态：草稿，仅用于 Path B 评审，不写入正式知识图谱正文。

## 错误特征

- 上游 Makefile 默认在构建阶段拉取或更新 `vlang/vc`，构建结果依赖实时网络与远端状态。
- V 的 stage1、stage2 和 final 编译器会在同一次构建中立刻执行；HarmonyOS PC 上未签名 ELF 不能作为下一阶段工具直接运行。
- 目标默认 `/tmp` 可能只读，普通 V 编译调用会因临时目录不可写失败。
- 默认 Boehm GC 在部分 HarmonyOS PC 环境中报告无效数据根范围，影响普通 V 程序编译/执行。
- Conan 2 `CMakeToolchain` 不存在 `extra_ldflags` 属性，test_package 可执行链接标志需要走 `extra_exelinkflags`。

## 根因

自举语言编译器不是单次 C/C++ 编译。它通常同时依赖固定 bootstrap 源、阶段产物可执行权限、安装后的源码根布局和运行时临时目录。V 0.5.2 还把真实编译器与 `cmd`、`vlib`、`thirdparty` 目录绑定在同一 vroot 下，单独安装一个 `bin/v` 二进制不足以让消费者编译程序。

## 可复用规则

1. 在 `source()` 中下载并校验主源码和 bootstrap 源，构建阶段只使用本地文件，不在 `build()` 中 `git clone`、`git pull` 或下载 `vc`。
2. 只运行可复现的本地 bootstrap 目标，例如 `make -f Makefile -j1 v VCFILE=v.c`。
3. 在 `settings.os == "OHOS"` 时，对 stage1、stage2、final compiler 和 test_package 生成的可执行文件使用 `binary-sign-tool` 签名，并恢复执行位。
4. 为 build、package wrapper 和 test_package 设置 recipe-owned `TMPDIR`、`TMP`、`TEMP`，避免依赖只读 `/tmp`。
5. 将真实编译器和源码根安装到 `share/v`，`bin/v` 只作为 wrapper 进入真实 vroot；OHOS wrapper 对普通编译调用追加 `-gc none`。
6. Conan 2 CMake test_package 如果只需要影响消费者可执行程序或 CMake 探测链接，使用 `toolchain.extra_exelinkflags.append(...)`，不要使用不存在的 `extra_ldflags`。

## 验证证据

- PR #3464 当前 clean rebase 后的 Vlang 配方保留固定 `v` 与 `vc` 两份源码输入，公共 diff 同时包含 `archives/v/vlang/0.5.2/**` 和本草稿。
- HarmonyOS PC 真机旧执行记录：`d870d160a793e689bed3bcfa5f2fee1c8ffc5890` 上游 `make check` 为 `3124/3738`，安装后消费者测试为 `1/1`。该结果不冒充当前 head 新测试率，只说明规则来源。
- 当前 head 的 CI #25063 已在平台侧通过 Conan `test_package`、L0 与 L1；此前同一 clean-scope head 的失败指纹为 `CMakeToolchain` 无 `extra_ldflags`，已由 `extra_exelinkflags` 修复。

## 禁止做法

- 不要在 `build()` 阶段联网拉取 bootstrap 仓库或使用未锁定的 bootstrap 源。
- 不要把未签名的阶段产物直接作为 OHOS 下一阶段编译器执行。
- 不要把跳过、失败或旧 head 的上游测试结果写成当前 head 通过率。
- 不要在 Conan 2 `CMakeToolchain` 上使用 `extra_ldflags`。

## 关联

- PR：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/3464
- 相关知识：E106（自举产物执行权限）、E128（OHOS ELF 签名/执行边界）
