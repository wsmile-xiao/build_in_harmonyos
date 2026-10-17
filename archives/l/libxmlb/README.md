# libxmlb

## 简介
libxmlb 是一个高效的 XML 二进制 blob 查询库，主要用于 fwupd 等项目的快速 XML 解析。它将 XML 文件编译成二进制格式，提供极速查询能力。

## OHOS 适配（conan，0.3.19）

### 依赖（ohpcd 制品仓已发布）
- glib/2.88.3（共享构建，GObject 类型系统一致性；内嵌 proxy-libintl，
  历史 g_libintl_* 链接问题不复存在）
- liblzma/5.8.1、zstd/1.5.7.1（lzma/zstd 压缩支持，上游 auto 特性显式启用）

### 关键适配点
- **glib .pc 修正层**：glib 安装 .pc 为 prefix=/ 且 Requires 列静态内部依赖，
  配方内复制重写（prefix + 剥离虚假 Requires）并置于 PKG_CONFIG_PATH 首位；
  gio-unix-2.0 由此可解析，xb-tool 的 SIGINT 处理保留（无裁剪）
- **ELF 重签**：meson install 改写 ELF 使 lld 链接期自签失效 → 安装后
  binary-sign-tool 重签（E077 对策）
- **.so 别名物化**：libxmlb.so.2/libxmlb.so 物化为常规文件（HMDFS）
- **禁用 introspection/gtkdoc**（OHOS worker 无对应工具，GIR 为绑定产物非 C API）
- **测试**：上游 49/49 全过（xb-self-test 原生执行）；测试数据 test.xml.xz/.zst
  覆盖 lzma/zstd 特性

## 依赖
- glib/2.88.3、liblzma/5.8.1、zstd/1.5.7.1

## 功能验证
```
pkg-config --modversion xmlb
# 输出: 0.3.19
```

xb-tool 用法（test_package 的 test() 以 conanrun 环境真实执行 compile+query
并随 CI 日志留档；裸跑需 LD_LIBRARY_PATH 指向包 lib/ 与 glib lib/）：
```bash
xb-tool compile out.xmlb in.xml    # XML → 二进制 blob
xb-tool query out.xmlb "xpath"     # XPath 查询
xb-tool dump out.xmlb              # blob 转储
```

## 预编译包内容
- bin/xb-tool
- lib/libxmlb.so.2.0.0 + 物化别名（.so.2/.so）
- lib/pkgconfig/xmlb.pc
- include/libxmlb-2/（xmlb.h + libxmlb/xb-*.h）

## 参考
- 源码: https://github.com/hughsie/libxmlb
- 相关项目: fwupd
