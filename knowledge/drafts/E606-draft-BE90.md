# E606 — OHOS 系统 gdbus-codegen shebang 不可用，meson 须用 native file 声明 wrapper

## 错误特征
```
[code=126] libmalcontent/tests/accounts-service-iface.h
/data/service/hnp/bin/gdbus-codegen --interface-info-header --output ...
/bin/sh: /data/service/hnp/bin/gdbus-codegen: No such file or directory
```
meson 配置阶段却显示 `Program gdbus-codegen found: YES (/data/service/hnp/bin/gdbus-codegen)`。

## 触发条件
- 构建系统: meson（gnome.gdbus_codegen）
- 阶段: configuration（find_program）/ compilation（执行 codegen）
- 系统 PATH（/data/service/hnp/bin）含指向旧版 glib 2.38 的 gdbus-codegen，shebang 为 `#!/usr/bin/python3`（普通路径无该解释器）

## 根因分析
OHOS 设备 `/data/service/hnp/bin/gdbus-codegen` 是 glib 2.38 的符号链接，脚本 shebang 写死 `#!/usr/bin/python3`，而 OHOS 无 `/usr/bin/python3`（python3 在 /data/service/hnp/bin）。meson `find_program('gdbus-codegen')` 只检查 PATH 命中即 YES，运行时 `/bin/sh` 解释 shebang 失败报 "No such file or directory"（code 126）。只改 PATH 前置不可靠：Meson.configure 用 `env=conanbuild` 会覆盖环境 PATH，generators_folder 前置经常不生效。

## 解决方案

### 推荐方案
1. conanfile generate() 从 glib 依赖包复制可用 gdbus-codegen，在 generators_folder 生成同名 wrapper（shebang `#!/usr/bin/env python3` + runpy 转发到 glib 包内脚本）：`sys.argv = [glib_bin/gdbus-codegen] + sys.argv[1:]; runpy.run_path(...)`
2. wrapper 路径写入 `conan_meson_native.ini` 的 `[binaries]` 段：`gdbus-codegen = '<wrapper>'`——meson find_program 查找顺序 native file [binaries] 优先于 PATH，彻底绕开系统坏脚本
3. 同时在 gio-2.0.pc 写入 `gdbus_codegen=<wrapper>` 变量（meson find_tool 回退通道）

### 禁止做法
- ❌ 依赖修改系统 /data/service/hnp/bin/gdbus-codegen（受保护环境目录）
- ❌ 只往 PATH prepend generators_folder 而不写 native file（env=conanbuild 覆盖，实测无效）

## 验证
```bash
# 修复前
ninja -C builddir accounts-service-iface.h  # FAILED: code=126 No such file or directory
# 修复后（native file [binaries] 声明 wrapper）
ninja -C builddir                           # Generating accounts-service-iface.h 通过
```

## 适用与不适用边界
- 适用：OHOS 等系统 PATH 含坏 shebang gdbus-codegen、且用 meson gnome.gdbus_codegen 的项目
- 同为 /data/service/hnp/bin 下 glib 工具（glib-mkenums 等）不可用时，同思路可推广：生成 wrapper + native file [binaries] 声明
- 不适用：Linux 桌面（/usr/bin/gdbus-codegen shebang 正常）；项目无 gnome 模块调用

## 关联条目
- 相关（find_program 断链）: E556 草稿（glib-mkenums），本文为其 meson + shebang 变体
- 相关（同为 OHOS 工具链路径）: E540（PATH 缺 /data/service/hnp/bin）