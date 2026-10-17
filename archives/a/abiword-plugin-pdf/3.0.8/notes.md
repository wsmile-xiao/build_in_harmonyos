# abiword-plugin-pdf 3.0.8 适配笔记

## 状态
- conan-verify 通过（G0-G4 + L2/L4/L5），待 CI 验证
- 插件：PDF 导出插件（libgsf 处理），源文件 plugins/pdf/xp/ie_imp_PDF.cpp

## 适配要点（相对 eml 模板的差异）
1. **TOOLKIT_GTK_ALL**：AbiWord 非 darwin/mingw 平台 TOOLKIT 硬编码 "gtk"
   → config.h 定义 TOOLKIT_GTK_ALL → ut_misc.h include <gtk/gtk.h>（OHOS 无 gtk）
   → build() 中从 config.h 移除该宏（插件代码不用 gtk API）
2. **boost 真实依赖**：pdf 头文件链（pd_Document.h）真实使用 boost::shared_ptr
   → requires boost/1.91.0.1.1 + CPPFLAGS 注入（eml 的 stub version.hpp 不够）
3. 其余沿用 eml 模板：autogen 自举、E114 ac_tmp、PkgConfigDeps、DEPS_CFLAGS/LIBS

## 依赖
- libgsf/1.14.53, libpng/1.6.58, libjpeg/10, zlib/1.3.1.1(override),
  glib/2.84.0, libxml2/2.15.3, fribidi/1.0.16, boost/1.91.0.1.1
- tool_requires: automake/1.18, libtool/2.5.4
