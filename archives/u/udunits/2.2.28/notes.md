# udunits 2.2.28 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build udunits 2.2.28 --url=...`
2. 安装依赖 expat 2.7.1（cmd-pkgs 预编译包）
3. `autoreconf -fi`（源码只有 configure.ac，需生成 configure）
4. `./configure --prefix=$DEFAULT_PREFIX LDFLAGS="-Wl,-rpath,\$ORIGIN/../lib"`
5. `make -j1`
6. `make install DESTDIR=$TEST_PREFIX`
7. 修复 HMDFS 软链接问题（共享库 .so 和 .so.N 用 cp 替代 ln -s）
8. `ohc-run.py verify-build` → PASS
9. `ohc-run.py package` → udunits-2.2.28-ohos-aarch64.tar.gz (1410KB)
10. `make install`（不带 DESTDIR） + 用户验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本不存在 | 源码只含 configure.ac | `autoreconf -fi` 生成 |
| 2 | version.texi 被损坏 | mdate-sh 脚本将环境变量写入文件 | 从 .orig 恢复 version.texi |
| 3 | 运行时无法加载共享库 libudunits2.so.0 | HMDFS 软链接不被 musl linker 解析 | 用 `cp` 替代 `ln -s` 创建 libudunits2.so 和 libudunits2.so.0 |
| 4 | CUNIT 未检测到 | 非核心依赖 | 不影响核心功能（仅影响 unit test） |
| 5 | manifest 缺少 build_system 字段 | 模板使用 system 而非 build_system | 修改为 build_system: autotools |

## 源码修改

- 0001-aclocal.m4.patch（autoreconf 生成）
- 0002-config.h.in.patch（autoreconf 生成）

## 依赖版本

- expat 2.7.1（cmd-pkgs 预编译包）
- libc (musl, HongMeng Kernel 1.12.0 aarch64)

## 验证结果

```bash
# udunits2 基本功能
~/usr/local/bin/udunits2 --version
# 输出: Usage 信息（不支持 --version 选项）

# 单位转换测试
echo "1 m\nft\n" | ~/usr/local/bin/udunits2 ~/usr/local/share/udunits/udunits2.xml
# 输出: 1 m = 3.28084 ft

# make check 通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| udunits-2.2.28-ohos-aarch64.tar.gz | 1410KB | 预编译包 |
| 0001-aclocal.m4.patch | - | autoreconf 生成补丁 |
| 0002-config.h.in.patch | - | autoreconf 生成补丁 |

## 注意事项

- HMDFS 文件系统不支持共享库软链接被 musl linker 解析，打包时必须用实际文件替代软链接
- 源码不含 configure，需要 autoreconf -fi 先生成
- 需要设置 LDFLAGS="-Wl,-rpath,\$ORIGIN/../lib" 以支持相对路径 RUNPATH

---
**编译结束**: 2026-05-25 22:46
**最终状态**: built
---

**编译结束**: 2026-05-26 16:05
**最终状态**: published
