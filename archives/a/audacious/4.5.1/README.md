# audacious 4.5.1 适配说明

## 构建系统

audacious 使用自研 `buildsys.mk` 构建系统（非 automake），关键适配点：

1. **仅源内构建**：`buildsys.mk` 无 VPATH 支持，`layout()` 必须 `folders.source == folders.build`
2. **无自动化测试**：`buildsys.mk` 无 check 目标、无 TESTS、无 tests/ 目录
3. **GIO 检测**：`AUD_COMMON_PROGS` 强制检测 `gio-2.0/gio-unix-2.0`（即使 D-Bus 已禁用），OHOS glib 包不含 `gio-unix-2.0.pc`，需预设 `GIO_CFLAGS`/`GIO_LIBS` 跳过检测
4. **umask 077**：`config.status` 用 `umask 077` 创建临时目录，OHOS 沙箱下不可写（E011）

## 依赖

- glib/2.88.0（configure 检测 glib-2.0 >= 2.32）
- pcre2/10.45（glib 依赖）
- zlib/1.3.1（glib 依赖）

## 补丁

- 0001-config.guess-ohos.patch：config.guess 添加 aarch64 OHOS/HarmonyOS 检测
- 0002-config.sub-ohos.patch：config.sub 添加 ohos/HarmonyOS 系统识别

## 测试结果

- 上游测试：0（无自动化测试）
- test_package：3/3 PASS
  - `audacious --version` → `Audacious 4.5.1 (unknown build)`
  - `libaudcore.so: OK`
  - `libaudtag.so: OK`
