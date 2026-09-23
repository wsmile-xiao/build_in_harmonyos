# libmobi — MOBI 电子书格式解析库

[libmobi](https://github.com/bfabiszewski/libmobi) 是用 C 编写的 MOBI/PRC/AZW/AZW3（KF8）
电子书格式解析库。它读取 PalmDB 容器、MOBI 头、EXTH 元数据与记录结构，支持：

- 完整文档解析（KF7/KF8 rawml 重建、HTML 拆分、资源文件解码）
- 元数据读写（title/author/ISBN 等 EXTH 记录）
- DRMed 文档解析（PID/serial 凭据，mobidrm 工具）
- 从零构造 MOBI 文档（write API，配合 miniz 产出 EPUB）
- 命令行工具 `mobitool`（转换/导出）与 `mobimeta`（元数据查看/修改）

## OHOS 适配要点

- **构建系统**：autotools。GitHub tag tarball 仅含 configure.ac + autogen.sh（无
  configure），配方内 `autoreconf -fi` 引导，等效上游 autogen.sh。
- **自包含配置**：`--with-zlib=no --with-libxml2=no`，压缩走内置 miniz、XML 走内置
  xmlwriter——设备上无 zlib/libxml2 开发头文件也可构建，且零外部 Conan 依赖。
- **上游测试**：`make check` 走 bash 脚本 + 样本 md5 比对；configure 探测到 toybox
  `md5sum` 时拼 `-t` 参数（toybox 不支持）导致全部 SKIP，须 `MD5PROG=md5sum` 环境变量覆盖。
- **产物**：`libmobi.so`（仅共享库）、`mobi.h`、`mobitool`/`mobimeta`/`mobidrm`
  可执行文件、`libmobi.pc`、man 页。

## 依赖

- 编译/运行：无（internal libs 配置）；默认配置下可选 zlib 与 libxml2。
- 测试：bash、md5sum。

## 参考资料

- 上游仓库：<https://github.com/bfabiszewski/libmobi>
- API 头文件：`src/mobi.h`（MOBI_EXPORT 函数族）
