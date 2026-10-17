# abiword-plugin-docbook 3.0.8 适配笔记

## 状态
- 基于 abiword-plugin-pdf/sdw 修复版模板（依赖 libgsf/1.14.58 + glib components include）
- 插件：AbiWord docbook 插件（libgsf 处理），源文件 plugins/docbook/

## 适配要点
1. TOOLKIT_GTK_ALL 宏移除（OHOS 无 gtk）
2. boost/1.91.0.1.1 真实依赖 + 全量 src xp include 注入
3. 依赖 libgsf/1.14.58 + glib/2.84.0.1 + libxml2/2.15.3.1（匹配制品仓二进制）
4. glib components include 兼容读取

## 依赖
- libgsf/1.14.58, libpng/1.6.58, libjpeg/10, zlib/1.3.1.1(override),
  glib/2.84.0.1, libxml2/2.15.3.1, fribidi/1.0.16, boost/1.91.0.1.1
- tool_requires: automake/1.18, libtool/2.5.4
