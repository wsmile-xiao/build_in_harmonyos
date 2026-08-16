# gnome-autoar 0.4.5 路径 B 候选说明

## 申请范围

- 任务：`gnome-autoar/0.4.5`
- 关联 Issue：`#2147`
- 分支：`feat/gnome-autoar-0.4.5-2147`
- 申请路径：路径 A（基础适配）+ 路径 B（贡献创新）
- 路径 B 类型：困难库适配分析报告，最终以评审委员会审核为准

主线原归档只有 `manifest.yaml`、`notes.md` 和质量报告等元数据，没有
`conanfile.py`、`conandata.yml`、有效补丁或 `test_package`。本次工作补齐可复现的
Conan 2 配方、上游测试执行和消费者测试，并将真机适配过程中的多层问题归纳为可复用
的 Meson/GLib 交叉构建方案。

## 上游测试基线

上游 `tests/test-extract-unit.c` 注册 22 个 GLib 测试项，覆盖普通与加密归档、冲突
处理、符号链接、路径净化和只读目录。适配后没有删除测试注册项：

| 口径 | 上游 | HarmonyOS 真机 |
|---|---:|---:|
| 注册测试项 | 22 | 22 |
| 通过 | 未在上游平台重跑 | 18 |
| 失败 | 未在上游平台重跑 | 0 |
| 能力受限跳过 | 未在上游平台重跑 | 4 |
| Conan 消费者测试 | 0 | 1 |

4 个跳过项均有独立能力依据：设备沙箱禁止创建符号链接 2 项；当前
`libarchive/3.8.7` 未启用 crypto backend 2 项。加密用例会先执行解密路径，仅在
收到明确的 `Decryption is unsupported` 错误后动态跳过，避免掩盖其他回归。

## 困难点与根因链

| 阶段 | 现象 | 根因 | 处理 |
|---|---|---|---|
| Meson 依赖探测 | `pkgconf` 无法启动或加载错误库 | runner 上 `pkgconf` 与旁路 `libpkgconf.so.7` ABI 不匹配 | 在 build 目录复制匹配的 `libpkgconf.so.7.0.0`，通过私有 wrapper 调用 |
| GLib 代码生成 | `glib-mkenums` 权限拒绝 | 缓存脚本所在目录受执行策略限制 | 使用 Python 解释器显式执行脚本，不依赖可执行位 |
| 静态库归档 | Meson 找不到 archiver | OHOS cross file 未稳定提供 `ar`/`ranlib` | 从 SDK 编译器同目录解析并注入 `llvm-ar`、`llvm-ranlib` |
| 上游符号链接测试 | `ln -s` 与测试均返回权限拒绝 | HarmonyOS 应用沙箱禁止符号链接 | 每个用例先运行时探测，仅对“不支持/权限拒绝”标记 skip |
| 加密归档测试 | `Decryption is unsupported` | 已发布 libarchive 包没有 crypto backend | 仅对精确能力错误动态 skip；依赖能力留给 libarchive 独立任务 |
| 消费者测试 | CMake 不可用 | 真机 runner 没有可用 CMake | test_package 改用 Meson，继续验证真实公共 API 和链接产物 |

问题不是单一编译报错，而是工具运行时 ABI、脚本执行策略、交叉归档工具、设备文件系统
能力和已发布依赖特性的连续组合。最终通过 14 轮隔离 shadow CI 将每层问题分别定位，
没有修改设备全局库、共享 Conan cache 或 CI runner。

## 可复用方案与边界

### 1. 构建工具运行时私有化

当 runner 上的构建工具和共享库版本漂移时，只在当前 Conan build 目录组合工具及其匹配
运行库，再由 wrapper 设置私有加载路径。该方案适用于 `pkgconf` 等宿主构建工具，避免
污染设备全局安装；不能用于掩盖目标库自身缺失的运行时依赖。

### 2. 受限目录中的解释器调用

缓存内 Python 或 shell 脚本无法直接执行时，通过已签名/允许执行的解释器显式调用。
本库用于 `glib-mkenums` 和 wrapper，适用于其他 GLib/Meson 项目的代码生成阶段。

### 3. Meson 交叉归档工具显式注入

从 OHOS SDK 编译器目录解析 `llvm-ar` 和 `llvm-ranlib`，写入 Conan 生成的 Meson
toolchain。该方案适用于静态库构建，且保持工具版本与 clang 一致。

### 4. 能力驱动的测试跳过

先执行能力探针或目标操作，只对确定的平台限制进行最小范围跳过；不能按平台名批量跳过
整个测试套件，也不能把普通断言失败改成 skip。本次 18 个可执行用例保持上游断言不变。

## 消费者测试

`test_package/test.c` 调用公开 API 创建 `AutoarCompressor`，生成 ZIP，等待
`completed` 信号，并检查输出文件类型和非零大小。它验证了头文件、静态链接、GLib
事件路径和 libarchive 写入能力，不是只打印版本字符串的空壳测试。

## 最终真机证据

- Endpoint：`currentUser@10.62.218.131:2222`
- Runner：`codex-gnome-autoar-gnome-autoar-0.4.5-2147-infra-path-r22-20260816-122207-5462`
- Runner exit code：`0`
- Meson：`1/1 gnome-autoar:test-extract-unit OK`
- GLib：22 total，18 passed，0 failed，4 skipped
- Consumer：`gnome-autoar 0.4.5 consumer test: OK`
- L0/L1/L4/L5：pass
- L2：skip，库包没有 `bin/`，符合预期
- Build Summary：Total 1，Success 1，Failed 0
- Conan package：
  `gnome-autoar/0.4.5#af05c1ee735cf66ab1aef1a071ace687:bb9d1be0eae2ad3143ce25809ca7a579c938ccda#a92966c147c177f3b60b68d8c403fc3a`

复验命令：

```sh
CI_PACKAGES="archives/g/gnome-autoar/0.4.5" zsh ci/conan/build_and_test.sh
```

## 适配边界

- 本任务只修改 `archives/g/gnome-autoar/0.4.5/` 和直接相关的
  `knowledge/drafts/DRAFT-gnome-autoar-runtime-capability-skip-2147.{kv,md}`。
- 不把 libarchive crypto backend 适配混入本 PR。
- 不修改共享 runner、全局动态库、基础设施目录、正式知识条目或其他三方库归档。
- 4 个能力跳过项不是功能通过声明；依赖或沙箱能力变化后应恢复执行。
