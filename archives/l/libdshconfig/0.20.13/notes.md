# libdshconfig 0.20.13 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-14
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码下载并解压
2. 应用 3 个补丁（config.guess, config.sub, umask fix）
3. `./configure --disable-shared --enable-static`
4. `make -j1`
5. `make install`
6. `make check` — 3/3 测试通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 (2007-03-06 版本) | 原始 configure 使用的 config.guess 太旧 | 补丁 0004-config.guess.patch 更新 config.guess |
| 2 | config.sub 无法识别系统类型 | 原始 config.sub 太旧 | 补丁 0006-config.sub.patch 更新 config.sub |
| 3 | config.status 创建临时文件失败 "Permission denied" | autoconf 使用 `umask 077` 创建临时目录，HMDFS 文件系统不允许在权限为 700 的目录内创建文件 | 补丁 0001-configure-umask-022.patch 替换 `umask 077` 为 `umask 022` |

## Conan 配方设计

- 使用 conandata.yml 补丁管理所有源码修改（3 个 portability 补丁）
- conanfile.py build() 方法仅调用 apply_conandata_patches + autotools.configure/make
- 不依赖系统 automake（通过补丁替代运行时 config.guess/config.sub 复制）
- 静态链接（--disable-shared --enable-static）

## 依赖版本

无依赖

## 验证结果

```
make check 结果:
PASS: tests/test-basic.sh
PASS: tests/test-dshconfig-searchdata.sh
PASS: tests/test-longline.sh
# TOTAL: 3  # PASS: 3  # SKIP: 0  # FAIL: 0
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libdshconfig.a | 静态库 |
| include/libdshconfig.h | 头文件 |

## 注意事项

- HMDFS 文件系统不支持 `umask 077` 创建的目录内写文件，需改为 `umask 022`
- 原始 configure 基于 autoconf 2.61，config.guess/config.sub 需更新
- 无 bin/ 目录，纯库软件
- conanfile.py 不依赖系统 automake，所有修改通过 conandata 补丁处理
---

**编译结束**: 2026-08-17 15:43
**最终状态**: built
