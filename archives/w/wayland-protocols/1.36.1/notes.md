# wayland-protocols 1.36.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-07
- 编译器: clang/clang++（本包为纯数据包，无编译产物）
- 状态: built
- 上游版本: 1.36
- 适配版本: 1.36.1（R37 版本递增：conandata.yml URL 修正 + 配方清理）

## 版本递增说明

wayland-protocols/1.36 已发布到制品仓（2026-08-25），本次修改了 conandata.yml URL
（git archive URL → 官方 release tarball URL）和 conanfile.py 配方结构，
按 R37 需递增版本号。

## 编译步骤

```bash
# Meson configure (disable tests, wayland-scanner not available on OHOS)
meson setup builddir --prefix=$TEST_PREFIX -Dtests=false

# Build (no-op, data-only package)
ninja -C builddir

# Install XML protocol files + pkg-config
meson install -C builddir
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson tests=true 配置失败 | 测试依赖 wayland-scanner（wayland 包），OHOS 平台无此工具 | conanfile.py 中 `-Dtests=false` 禁用测试 |
| 2 | conandata.yml URL 指向 git archive 而非 release tarball | 初始模板使用了 archive URL，SHA256 不匹配 | 修正为官方 release downloads URL + 验证 SHA256 |
| 3 | pkg-config prefix 指向 `/`（根目录） | meson 默认 prefix=/ 导致 pc_sysrootdir 解析错误 | conanfile.py package() 中修正 .pc prefix 为包路径 |
| 4 | 版本已在制品仓存在 | 1.36 已发布，修改配方需递增版本 | 版本号从 1.36 递增到 1.36.1（R37） |

## 源码修改

无补丁。wayland-protocols 是纯数据包（XML 协议定义文件），meson 仅用于安装文件和生成 pkg-config。

## 依赖版本

- meson 1.12.0
- ninja 1.13.1
- clang 15.0.4（本包不需要，纯数据包）

## 上游测试

上游测试共 131 项，全部跳过（依赖 wayland-scanner 不可用）：

- 44 scan 测试：每个协议 XML 通过 wayland-scanner 扫描
- 44 pedantic C99 测试：每个协议用 -std=c99 -pedantic -Werror 编译
- 43 C++ 测试：每个协议头文件用 C++ -Wall -Werror 编译（xdg-foreign-unstable-v1 除外）

测试配置命令及结果：
```bash
$ meson setup builddir-test -Dtests=true
ERROR: Run-time dependency wayland-scanner found: NO
```

## 验证结果

```bash
$ find $TEST_PREFIX -type f | wc -l
45

$ find $TEST_PREFIX -name "*.xml" | wc -l
44

$ cat $TEST_PREFIX/share/pkgconfig/wayland-protocols.pc
prefix=...
pkgdatadir=${pc_sysrootdir}${datarootdir}/wayland-protocols
Name: Wayland Protocols
Description: Wayland protocol files
Version: 1.36
```

## 注意事项

- 本包为纯数据包（package_type="unknown"），无 .a/.so 编译产物
- 测试依赖 wayland-scanner（wayland 包），OHOS 平台暂不可用，全部 131 项测试跳过
- conanfile.py 在 package() 中修正 .pc prefix，确保下游 pkg_get_variable 可用
- conandata.yml 使用官方 release tarball URL（.tar.xz），非 git archive URL
---

**编译结束**: 2026-09-07 20:47
**最终状态**: built
