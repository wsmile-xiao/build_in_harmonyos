# gift — GNU Image Finding Tool

GNU Gift 是开源的基于内容图像检索（CBIR）系统：MRML 协议 C++ 服务端
（GIFTServer）+ 9 个共享库（libMRML、libGIFTAc*/libGIFTQu* 系列）+
24 个 Perl 客户端脚本，源自 2002 年 GNU 项目。

## 鸿蒙 PC 适配状态

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.1.9 | conan 配方已构建 | autotools in-source 构建，依赖 expat/2.8.4、libuuid/2.42.2 |

要点：
- 补丁修复 2002 年 autotools 2.13/libtool 1.4 在 HMDFS + toybox 环境
  下的 mktemp 权限、sed 缓冲上限问题，并完成 C++17/libc++ 迁移。
- Perl 访问器库按上游设计引用 perl 解释器符号，库本身不链 libperl；
  test_package 探针以桩符号满足 musl BIND_NOW 全量重定位。
- test_package 为链接期探针：exec 加载全部 9 库并真实调用
  libMRML createErrorMessage API。

详见各版本目录内 manifest.yaml / notes.md。
