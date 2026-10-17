# icu4c 78 适配笔记

## 编译环境
- 软件: icu4c (International Components for Unicode)
- 版本: 78 (上游 78.3)
- 构建系统: autotools (configure + make)
- 编译日期: 2026-07-22
- 编译器: clang 15.0.4 (HNP 工具链)
- 平台: OpenHarmony aarch64
- Conan profile: ohos-aarch64
- 状态: built

## 编译步骤

### 1. 源码获取
- 官方下载: https://github.com/unicode-org/icu/releases/download/release-78.3/icu4c-78.3-sources.tgz
- sha256: 3a2e7a47604ba702f345878308e6fefeca612ee895cf4a5f222e7955fabfe0c0
- 源码包结构: icu/source/{configure, configure.ac, ...}
- 解压后需将 source/ 内容移到根目录以匹配补丁路径

### 2. 应用补丁
14 个补丁全部为 OHOS 平台适配，通过 conandata.yml patches 声明 + apply_conandata_patches() 自动应用:
- 0001-0002: Doxyfile.in / Makefile.in 路径修复
- 0003-0005: configure.ac / icudefs.mk / icudefs.mk.in 平台检测
- 0006: .clang-format 格式修复
- 0007-0008: acinclude.m4 / aclocal.m4 宏修复
- 0009-0011: config.guess / config.sub 添加 OHOS 识别
- 0012-0013: install-sh / mkinstalldirs 权限修复
- 0014: runConfigureICU 添加 OHOS 配置

### 3. 额外源码修改（运行时 patch，不在 patches/ 中）
- configure 脚本 umask 077 → 022: HMDFS 文件系统上 umask 077 创建的目录无法写入（config.status Permission denied）

### 4. 配置选项
```bash
./configure --prefix=$PREFIX \
  --disable-shared \
  --enable-static \
  --with-data-packaging=static \
  --disable-layoutex
```
- --disable-shared --enable-static: 静态编译（R5/R26，避免 stubdata .so 导致 OHOS 动态链接器崩溃）
- --with-data-packaging=static: 数据嵌入静态库，避免运行时数据文件加载
- --disable-layoutex: 禁用不需要的 layoutex，减少编译时间

### 5. 编译
```bash
make -j1
```
- 使用 -j1 因为 HMDFS 不支持 make jobserver mkfifo

### 6. 安装
```bash
make install
```
- 需额外复制 LICENSE 到源码父目录（Makefile 引用 $(srcdir)/../LICENSE）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 源码下载超时 | 网络速度慢 (~18KB/s) | curl -C - 恢复下载，分3次完成 28MB |
| 2 | config.status Permission denied | HMDFS 不支持 umask 077 创建的目录写入 | 将 configure 中 umask 077 替换为 umask 022 |
| 3 | LICENSE 文件找不到 | 源码移动后 Makefile 相对路径不匹配 | package() 中复制 LICENSE 到父目录 |
| 4 | u_init() 编译错误 | 缺少 unicode/uinit.h 头文件 | 改用 #include <unicode/uclean.h>（u_init 声明位置） |
| 5 | conan-verify G1 路径错误 | find_project_dir() 返回 SKILL_ROOT | 设置 OHC_PROJECT_DIR 环境变量 |
| 6 | finish W3 超时 | 框架 600s 超时 < ICU 编译 12-15min | 框架限制，conan-verify 已独立验证通过 |

## 依赖版本

无外部依赖。ICU 是自包含的 C/C++ 库。

## 验证结果

```bash
# conan-verify: G0-G4 + L2/L4/L5 全部 PASS
# test_package: All ICU tests passed
# u_init() succeeded
# Unicode version 17.0.0.0
# u_errorName() returns: U_BUFFER_OVERFLOW_ERROR
# u_isalpha('A') = true
```

## 编译产物

| 文件 | 说明 |
|------|------|
| libicudata.a (33MB) | ICU 数据库（含全部 Unicode/CLDR 数据） |
| libicuuc.a (4.6MB) | 通用库（UTF 处理、字符属性等） |
| libicui18n.a (9.4MB) | 国际化库 |
| libicuio.a (113KB) | I/O 库 |
| libicutu.a (460KB) | 工具库 |

## 注意事项

1. ICU 必须静态编译：OHOS 动态链接器对 ICU stubdata .so 有崩溃问题
2. --with-data-packaging=static 将 ~33MB Unicode 数据嵌入 libicudata.a
3. HMDFS 限制：umask 077 不可用、make jobserver mkfifo 不可用
4. 14 个补丁全部为平台适配，无功能性修改
5. conanfile.py 中 source() 需将 source/ 子目录内容移到根目录以匹配补丁路径

---

**编译结束**: 2026-07-22 13:42
**最终状态**: built
