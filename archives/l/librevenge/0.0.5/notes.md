# librevenge 0.0.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-01
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: published

## 编译步骤

1. 下载源码: librevenge-0.0.5.tar.xz from SourceForge
2. 应用补丁: config.guess/config.sub (HarmonyOS 识别) + .rc 文件 + umask fix
3. configure --enable-static --disable-shared (R26: 系统同名库静态)
4. make -j1
5. make install (DESTDIR staging)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 OHOS | autotools 版本过旧 | 替换 config.guess/config.sub |
| 2 | .rc 文件缺失 | Windows 资源文件未包含 | 添加 .rc 补丁 |
| 3 | boost 头文件找不到 | conan 依赖未传递 | 添加 AutotoolsDeps 生成器 |
| 4 | cppunit 未找到 | 测试依赖非构建必需 | 设置 CPPUNIT_CFLAGS/LIBS 为空 |
| 5 | zlib 未找到 | conan 依赖未传递 | 添加 zlib 依赖 + ZLIB_CFLAGS/LIBS |
| 6 | config.status 权限拒绝 | E011: HMDFS umask 077 | patch: umask 077→022 |

## 源码修改

- patches/0001-config.guess.patch: HarmonyOS 平台识别
- patches/0002-config.sub.patch: HarmonyOS 平台映射
- patches/0003-0005: 添加 .rc 资源文件
- patches/0006-configure-umask-fix.patch: E011 umask 修复

## 依赖版本

- boost/1.90.0@ohpcd/stable (header-only)
- zlib/1.3.1

## 验证结果

- conan create: PASSED
- test_package: 100% tests passed (1/1)
  - librevenge_api_test: Passed (0.02s)

## 交付物

librevenge 产出 3 个静态库:
- librevenge-0.0.a (核心库)
- librevenge-generators-0.0.a (生成器)
- librevenge-stream-0.0.a (流处理)

头文件位于 include/librevenge-0.0/ 下。

## COMPLETED
最终状态: published
