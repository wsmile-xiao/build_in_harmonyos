# stiff 2.4.0.1 适配笔记

## 编译环境
- 构建系统: cmake（绕过 autotools，生成 conan-cmake 工程；上游 2.4.0 已验证方案迭代沿用）
- 编译日期: 2026-09-01
- 编译器: clang 15.0.4（OHOS aarch64, armv8）
- 状态: built

## 编译步骤

1. `source()`：下载官方 Debian orig 包 stiff_2.4.0.orig.tar.gz（sha256 d9a1504756…）与 libtiff 4.7.2 源码（sha256 672bd7d10a…）；
2. `build()`：在源码树 `conan-cmake/` 生成 CMake 工程——`add_subdirectory` 内嵌 libtiff（仅 zlib/jpeg codec，其余 tiff-tools/tests/docs/cxx/deflate/zstd/webp/lerc/jbig/lzma 全 OFF），`BUILD_SHARED_LIBS=OFF`；
3. 手工 `config.h`：`THREADS_NMAX 1` 关闭 pthread worker；`-fcommon` 兼容 2.4.0 legacy C 公共符号；`-Wno-error=format-security`；
4. `requirements()`: zlib/1.3.1.1、libjpeg/10（Conan 制品仓）；
5. `conan create`（ohos-aarch64 profile, clang 15）：构建 + test_package 全部通过，W3 本地 CI exit_code=0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github archive URL 下载连接被远端关闭 | github.com/.../archive/refs/tags 瞬时不可达 | 改用官方 deb.debian.org orig 包（R39 权威镜像），下载成功 |
| 2 | W3 L0k 门禁失败 commands_json_r38 | 迭代版本未同步 commands.json | 软件级 commands.json 补 2.4.0.1 条目 |
| 3 | W3 后 conandata.yml 被改写为 file:// 本地路径 | build_and_test.sh pre-download 原地改写 URL | 提交前恢复官方 URL（R39） |

## 依赖版本

- zlib/1.3.1.1、libjpeg/10（Conan 制品仓已发布）
- libtiff 4.7.2（固定 hash 内嵌源码，非 Conan 包）

## 验证结果

```bash
conan create . --version=2.4.0.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 构建通过；test_package 7 项断言全过（-v 版本输出含 2.4.0 / -d 默认配置 / -c FITS→TIFF 转换 / TIFF 魔数 II*\0|MM\0*）
python3 test_package/test_stiff.py <bin>/stiff  # exit 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/stiff | 944576 | FITS→TIFF 转换命令行工具（BigTIFF ON, libTIFF V4.7） |

## 注意事项

- 上游 stiff 2.4.0 无自动化测试套件（make check 为空壳 0 用例），功能验证由 test_package 承担；
- 上游版本号保持 2.4.0，包版本为 2.4.0.1（R37 适配后缀，制品仓同版本多 revision 不支持并存）。

## 结束

**编译结束**: 2026-09-01
**最终状态**: built
