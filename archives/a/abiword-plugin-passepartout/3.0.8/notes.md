# abiword-plugin-passepartout 3.0.8 适配笔记

## 状态
- 基于 abiword-plugin-pdf 3.0.8 模板批量生成（conan-verify 流程已验证）
- 插件：AbiWord passepartout 插件，源文件 plugins/passepartout/xp/

## 适配要点（继承 pdf 模板）
1. **TOOLKIT_GTK_ALL**：AbiWord 非 darwin/mingw 平台 TOOLKIT 硬编码 "gtk"
   → config.h 定义 TOOLKIT_GTK_ALL → ut_misc.h include <gtk/gtk.h>（OHOS 无 gtk）
   → build() 中从 config.h 移除该宏
2. **boost 真实依赖**：头文件链（pd_Document.h）使用 boost::shared_ptr
   → requires boost/1.91.0.1.1 + CPPFLAGS 注入
3. 沿用模板：autogen 自举、E114 ac_tmp、PkgConfigDeps、DEPS_CFLAGS/LIBS

## 依赖
- libgsf/1.14.53, libpng/1.6.58, libjpeg/10, zlib/1.3.1.1(override),
  glib/2.84.0, libxml2/2.15.3, fribidi/1.0.16, boost/1.91.0.1.1
- tool_requires: automake/1.18, libtool/2.5.4
