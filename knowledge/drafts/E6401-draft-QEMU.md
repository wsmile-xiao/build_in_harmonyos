# DRAFT-E6401: Meson 在 OHOS 上 host_os 'HarmonyOS' 不识别 + SDK 工具链不在默认 PATH + subproject wrap-git 不可达

- **触发实例**: qemu 11.1.1 OHOS armv8 适配（build_in_harmonyos archives/q/qemu/11.1.1，2026-09-22，分支 feat/qemu-11.1.1）
- **错误签名**: `unknown host machine system` / `Program llvm-ar not found` / `could not read from remote repository`
- **类别**: build-system, meson, platform, detection
- **严重度**: 1（blocking——不归一化则产物走非 Linux stub 路径，核心功能缺失）

## 症状（可复现）

1. OHOS SDK 的 meson 宿主三元组 system 为 `HarmonyOS`；QEMU `meson.build` 只按 linux/windows/... 分支，
   对未识别 host_os **不报错、静默回退非 Linux stub 代码路径**（CONFIG_LINUX 未启用，
   syscall wrapper/UFFD/SG_IO/PR manager 全部缺失），产物功能严重残缺。
2. meson 以裸名探测 `llvm-ar/llvm-ranlib/llvm-nm/llvm-strip/ninja`；SDK 编译器位于
   `/data/service/hnp/bin`，不在默认 PATH → 探测失败。
3. `[wrap-git]` 类型 subproject（如 dtc）尝试从 gitlab.com `git fetch`，OHOS 构建环境不可达。
4. 级联：host_os 归一化为 linux 后，QEMU 会尝试编译 `can_socketcan.c`（socket(PF_CAN)），
   OHOS 无 CAN 设备支持 → 必须配套跳过。

## 根因

OHOS 的 meson host system 命名不在上游 meson.build 的已知系统表中；构建系统对未知值采取
"静默回退"而非报错策略，导致错误不发生在 configure 阶段而延迟为功能缺失，极难定位。
工具链与网络问题（SDK 路径不在 PATH、gitlab 不可达）独立叠加，三者需同时解决才能进入正常编译。

## 方案（已验证，qemu 11.1.1 实测通过）

1. **patch 0001** `meson-build-harmonyos-linux`：meson.build 中 `host_machine.system()` 之后
   将 `HarmonyOS` 归一化为 `linux`，原值保留在 `host_os_orig`（供 0002 判断）。
2. **patch 0002** `can-skip-socketcan-on-harmonyos`：`host_os_orig` 非 linux 时跳过 `can_socketcan.c`
   （0001 的级联后果，两补丁必须配套）。
3. **patch 0003** `dtc-use-official-github-mirror`：dtc.wrap `[wrap-git]` → `[wrap-file]`
   官方固定版本 v1.6.1 tarball（含 source_hash）；`build()` 内另对带 bundled 源码的 subproject
   （dtc/keycodemapdb/softfloat 等）删除 `.wrap`，使 meson 直接用内置源码。
4. **conanfile generate()**：写独立 env 脚本（`qemu_env`，不用 conan 聚合脚本），
   `PATH` prepend `/data/service/hnp/bin` + define `AR/RANLIB/NM/STRIP`；
   configure 显式传 `--cc/--cxx` SDK 绝对路径。

## 验证

- `meson setup` 后 `meson-logs/meson-log.txt` 的 Host system = linux；`ninja` 使用 SDK 绝对路径工具链。
- 完整编译通过：`ninja -j` + `ninja install`（qemu 11.1.1 W3 本地 CI 日志，conan-verify G2 通过）。

## 禁止策略

- `--cross-file` 硬改 host=linux（configure 层与 meson 层须一致，否则 split-brain）。
- export SDK 路径到全局 PATH（污染其他包；R33：conan build() 不得依赖裸 shell 环境变量）。

## 关联条目

- E6402（同任务草稿）：meson 不写 $ORIGIN RUNPATH + package() 批量签名——本条目是其后置修复的前置（构建先通过）。
- E077：ELF 签名四步通用流程（E6402 引用）。
