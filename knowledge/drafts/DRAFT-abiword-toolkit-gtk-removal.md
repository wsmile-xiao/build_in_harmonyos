# DRAFT-abiword-toolkit-gtk-removal - AbiWord 类插件无 GTK 平台独立打包

> 正式编号未分配；合并/提升时由知识库维护流程分配下一个可用 E###。

## 错误特征

AbiWord 插件（`plugins/*/`）在 OHOS（无 GTK）上编译时：

- `gtk/gtk.h: No such file or directory`（任意 include `ut_misc.h` 的源文件）
- config.h 出现 `#define TOOLKIT_GTK_ALL`
- （附带）`boost::shared_ptr` 相关报错 → boost 头文件缺失

## 触发条件

- 目标是非 darwin/mingw 平台（OHOS 落入 `*) TOOLKIT="gtk"` 分支）。
- 插件源码 include 主程序的 `ut_misc.h`（所有 AbiWord 插件都 include）。
- OHOS 环境没有 gtk 发行包（无法用 `requires` 补齐）。

## 根因分析

AbiWord `configure.ac` 对平台 toolkit 的选择是硬编码的：

```m4
case ${host_os} in
  *darwin*) TOOLKIT="cocoa" ;;
  *mingw*)  TOOLKIT="win" ;;
  *)        TOOLKIT="gtk" ;;   # ← OHOS 走到这里
esac
```

→ `config.h` 定义 `TOOLKIT_GTK_ALL` → `ut_misc.h` 无条件 `#include <gtk/gtk.h>`。插件只要 include `ut_misc.h` 就编译失败。这不是插件的问题，是主程序配置系统对无 GUI 平台不友好的通用问题（同类：任何把 GUI toolkit 硬编码进 config.h 的程序插件）。

## 推荐方案

**前提判断**：插件源码是否直接 include/call `gdk_`/`gtk_` API。不调用的（pdf/passepartout/urldict/wml/xslfo/sdw/docbook/openxml）可适配；真调的（presentation 调 `gdk_pixmap_new`）不可适配，应止损 `env_unsupported`。

1. **删宏**：configure 之后，从 build/source 两处 `config.h` 删除该宏：
   ```python
   import re
   for _cfg_h in (os.path.join(self.build_folder, "config.h"),
                  os.path.join(self.source_folder, "config.h")):
       if os.path.exists(_cfg_h):
           _txt = open(_cfg_h).read()
           _txt = re.sub(r"^#define TOOLKIT_GTK_ALL[^\n]*\n?", "", _txt, flags=re.M)
           open(_cfg_h, "w").write(_txt)
   ```
   → `ut_misc.h` 走 `#else typedef void AbiNativeWidget` 分支。
2. **boost 真实依赖**：`requires("boost/1.91.0.1.1")` + generate() 注入真实 include 目录（`boost::shared_ptr` 在 `pd_Document.h` 真实使用，stub `version.hpp` 只骗过 configure 的 AX_BOOST_BASE，编译期不够）。
3. **全量 xp include**：一次性注入 src 下全部 xp 目录（af/ev、af/gr、af/tf、af/util、af/xap、text/fmt、text/ptbl、wp/ap、wp/impexp、wp/main）到 CXXFLAGS，`os.path.isdir` 过滤不存在的，避免"加一个缺一个"循环。
4. **readelf 测试**（上游无插件级测试时）：
   - ELF 有效：`readelf --dyn-syms` 能解析
   - 导出符号：`abi_plugin_register` / `abi_plugin_unregister` / `abi_plugin_supports_version`
   - FUNC 符号计数
   - 插件架构 = 主进程 dlopen，**不能**在 test_package 里 `dlopen` 独立加载（宿主 ABI 不在场，参考 E337）

## 验证方法

1. `conan create` 编译通过（OHOS profile）。
2. `readelf --dyn-syms plugin.so` 确认三个 `abi_plugin_*` 符号。
3. CI `conan-build-test` 绿。
4. 本地 conan-verify G0-G4 + L2/L4/L5。

## 禁止事项

- ❌ stub/fake gtk 头文件：掩盖 GUI 依赖，产物在真实主机 dlopen 失败。
- ❌ 保留 `TOOLKIT_GTK_ALL`：`ut_misc.h` 仍会 include gtk 头。
- ❌ 对真调 gdk API 的插件（presentation/s5）强行适配：应止损。

## 同类问题

- 任何"GUI 程序插件需要独立打包到无 GUI 平台"的 autotools 项目（AbiWord 插件族 8 个、及同类 word processor 插件架构）。
- 任何 configure 硬编码 toolkit/平台宏导致头文件条件编译错误的项目。

## 证据

- 触发：abiword-plugin-pdf 3.0.8（PR #6781）起，8 个插件全部编译通过（pdf/passepartout/urldict/wml/xslfo/sdw/docbook/openxml）。
- 止损反例：presentation（gdk_pixmap_new）、s5（渲染+应用层）→ `env_unsupported`。
- 结果：CI 大部分绿；readelf 符号验证通过。
