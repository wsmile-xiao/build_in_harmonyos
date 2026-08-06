# fastjar 0.98 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤
1. 下载源码并解压
2. 应用 4 个补丁（config.guess, config.sub, configure, configure.ac）
3. 修复 shebang: `/bin/sh` → `/system/bin/sh` (OHOS 平台无 /bin 目录)
4. `./configure --prefix=$DEFAULT_PREFIX`
5. `make -j1`
6. `make install` 到 staging 目录
7. 验证: `fastjar --version` 输出 "jar (fastjar) 0.98"
8. Conan 配方生成与验证通过

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 平台无法识别 | config.guess/config.sub 不认识 OHOS | 更新 config.guess 和 config.sub |
| 2 | configure 脚本报错 | configure.ac/configure 缺少 OHOS 支持 | 修补 configure.ac 和 configure |
| 3 | 脚本无法执行 | OHOS 无 /bin/sh, shebang 指向不存在的路径 | conanfile.py build() 中替换为 /system/bin/sh |
| 4 | HMDFS 权限问题 | umask 077 在 HMDFS 上导致 config.status 无法写入 | configure 和 configure.ac 中移除 umask 077 |

## 源码修改
| 文件 | 修改内容 | 补丁文件 |
|------|----------|----------|
| config.guess | 平台适配 (OHOS 识别) | 0001-config.guess.patch |
| config.sub | 平台适配 (OHOS 识别) | 0002-config.sub.patch |
| configure | 移除 umask 077 | 0003-configure.patch |
| configure.ac | 覆盖 AS_TMPDIR | 0004-configure.ac.patch |

## 运行时修复 (conanfile.py build())
- shebang 修复: `replace_in_file(self, path, "#!/bin/sh", "#!/system/bin/sh")` for configure, compile, install-sh, config.guess, config.sub

## 依赖版本
- zlib/1.3.1 (from ohpcd artifact repo)

## 验证结果
- conan-verify: PASS (G1/G2/G3/G4 + L2/L4/L5)
- W3 本地 CI 模拟: PASS
- W4 Pre-PR 审计: PASS (P0=0, P1=0)

---

**编译结束**: 2026-08-06
**最终状态**: published
