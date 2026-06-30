# pacparser 1.5.0 适配笔记

## 编译环境
- 构建系统: 自定义 Makefile（非autotools，内嵌QuickJS JS引擎）
- 编译日期: 2026-06-11
- 编译器: clang 15.0.4
- CFLAGS: -fPIC -O2
- 状态: built

## 对话记录

### 对话1: 初始化与编译 (2026-06-11)

**configure 参数**: 无（pacparser使用自定义Makefile，由创建的configure wrapper脚本处理 `--prefix`)
**构建命令**: `make VERSION=v1.5.0 PREFIX=$DEFAULT_PREFIX`（从顶层目录）
**耗时**: 约5分钟（含QuickJS编译）

**主要修改**:
1. 顶层Makefile: 重写为委派到src/Makefile（+23/-11行），添加all/build/install/clean目标
2. configure（新增）: 创建configure wrapper脚本（+38行），生成version.mk并接受--prefix参数
3. src/Makefile: SHELL改为/bin/sh（+1/-5行），install目标改为mkdir+cp+chmod（+7/-18行）

**遇到的问题**:
| # | 问题 | 根因 | 解决 |
|---|------|------|------|
| 1 | SHELL=/bin/bash找不到 | OpenHarmony无/bin/bash | 改为/bin/sh |
| 2 | git describe获取VERSION失败 | tarball无git仓库 | 创建configure脚本生成version.mk |
| 3 | GNU install命令不可用 | OpenHarmony无coreutils install | Makefile中用mkdir+cp+chmod替代 |
| 4 | 顶层Makefile默认目标为docker_multiarch | 原Makefile仅Docker构建 | 重写添加all/build目标 |
| 5 | ln -sf在HMDFS不安全 | R5铁律 | 改为rm -f && ln -s |
| 6 | G0 clean-verify期望./configure | pacparser无configure脚本 | 创建configure wrapper |

**编译结果**: 编译成功，测试通过

### 对话 #2: 修复G0验证与门禁 (2026-06-11)

**问题**: G0 clean-verify失败，质量门禁G4不通过
**解决**:
1. 创建configure wrapper脚本使G0可以运行./configure
2. 修改顶层Makefile使默认目标为实际编译而非docker
3. 修改src/Makefile install目标使DESTDIR模式正确工作
4. 添加manifest.yaml的build_system顶层字段
5. 修复manifest.yaml patches_applied列表

**最终结果**: G0/G1-G4全通过，质量报告PASS

## 编译步骤

1. `ohc-run.py init-build pacparser 1.5.0 --url=https://github.com/manugarg/pacparser/archive/refs/tags/v1.5.0.tar.gz --no-download`
2. `bash ./configure --prefix=$DEFAULT_PREFIX`（生成version.mk）
3. `make VERSION=v1.5.0 PREFIX=$DEFAULT_PREFIX`（编译QuickJS + pacparser库 + pactester）
4. `NO_INTERNET=1 bash tests/runtests.sh` → 全部通过
5. `make install DESTDIR=$TEST_PREFIX`（Staging安装）
6. Staging验证 → 通过
7. `ohc-run.py package pacparser 1.5.0`（预编译包制作）
8. `make install`（本地安装，不带DESTDIR）
9. 本地验证: pactester -v → v1.5.0 ✅
10. `ohc-run.py finish pacparser 1.5.0 built`
11. `ohc-run.py verify-build pacparser 1.5.0` → G0/G1-G4全通过

## 验证结果

```bash
$ pactester -v
v1.5.0

$ pactester -p proxy.pac -u http://www.google.com
isResolvable

$ pactester -p proxy.pac -u http://www2.manugarg.com
plainhost/.manugarg.com

$ pactester -p proxy.pac -c 192.168.1.134 -u http://www.google.com
isResolvable

$ NO_INTERNET=1 bash tests/runtests.sh
All tests were successful.
```

G0 clean-verify: PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pacparser-1.5.0-ohos-aarch64.tar.gz | 3581KB | 预编译包（含ELF签名） |
| pacparser-1.5.0-ohos-aarch64-debug.tar.gz | 446KB | debug符号包 |
| 0001-Makefile.patch | 1520字节 | 顶层Makefile重写 |
| 0002-configure.patch | 1190字节 | configure wrapper脚本 |
| 0003-src-Makefile.patch | 2723字节 | src/Makefile SHELL+install修改 |

## 注意事项

- pacparser使用自定义Makefile而非autotools，构建命令为 `make`（从顶层目录）
- 内嵌QuickJS JS引擎（v1.5.0已从SpiderMonkey迁移到QuickJS），无需外部依赖
- Internet测试需设NO_INTERNET=1
- GNU install命令在OpenHarmony不可用，Makefile中已用mkdir+cp+chmod替代
- pactester --version不支持，需使用 -v 参数

---

**编译结束**: 2026-06-11
**最终状态**: built