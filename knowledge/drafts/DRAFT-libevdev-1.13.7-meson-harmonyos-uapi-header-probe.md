# DRAFT-libevdev-1.13.7-meson-harmonyos-uapi-header-probe

> Contributor: 2301_76770579 | Status: Draft | Updated: 2026-09-08
> Source: libevdev 1.13.7 HarmonyOS PC 适配（Meson；1.13.3 升版）

## 现象（Meson 平台/工具链坑）

libevdev（Linux evdev 事件处理库，Meson）迁 OHOS aarch64（musl）时配方侧遇到：

| # | 坑 | 直接现象 |
|---|---|---|
| 1 | `host_machine.system()` 在 OHOS 返回 **'harmonyos'** | meson.build 探 `include/linux/<system>/input.h` → 上游无 `include/linux/harmonyos/`，找不到内核 UAPI 头 |
| 2 | ninja 打包静态库需 ar/ranlib，OHOS clang 环境 PATH 无 | `ar: not found` / RANLIB 缺失（工具链由 Conan profile 提供） |
| 3 | HMFS 拷贝/归档丢符号链接链 | `meson install` 的 `libevdev.so → .so.2 → .so.2.3.0` 别名在包目录不完整 → 消费端解析失败 |
| 4 | 上游测试全需外设 | 6 个 suite 全标 `needs-uinput`（需 `/dev/input/uinput`），构建机无 → 不可实跑 |

## 修复（配方侧，升版沿用 1.13.3 方案）

1. **UAPI 头**：build() 幂等建 `include/linux/harmonyos/`，把 `input.h`/`input-event-codes.h`
   软链自同树 Linux UAPI 头（HarmonyOS 内核 = Linux）。
2. **ar/ranlib**：从 profile `tools.build:compiler_executables` 取 clang 路径推导同目录
   `llvm-ar`/`llvm-ranlib`，以 `AR`/`RANLIB` 环境变量注入。
3. **soname 别名**：shared 时 package() 补 `libevdev.so.2` → `libevdev.so` 别名软链
   （HMFS 安全）。
4. **TMPDIR**：OHOS `/tmp` 只读（E002）→ 指用户可写目录。
5. **测试如实报告**：上游 6 个 `needs-uinput` suite 构建机无法实跑（1.13.3 同口径已在库
   published）；以 test_package 消费者 API 覆盖作 L1（event 名称查询 + 对象生命周期）。

升版核对点：`project version 1.13.7`、soname 仍 2.3.0、`-Dtests/-Dtools/-Ddocumentation`
选项、harmonyos 头查找逻辑均不变 → 方案整体沿用。

## 验证证据

- 软链建好后 ninja 不再因 input.h 缺失失败。
- conan create（OHOS aarch64 CI）通过；test_package 输出 `libevdev test: OK`。
- 包内 `lib/libevdev.so*` 别名链齐全。

## 作用域与维护条件

- 作用域：任何「Meson 以 `host_machine.system()` 探平台头 / 内核 UAPI」的库迁 OHOS；
  依赖 ninja 静态打包的库（ar/ranlib 注入）；带 soname 链共享库（HMFS 别名补链）。
- 上游若增加 `harmonyos` 头目录或提供 cross file system 映射，第 1 条可简化。
- 禁忌：不得谎报 needs-uinput 测试通过；不得把生成的头目录 commit 进源树；
  不得硬编码 ar 路径。
