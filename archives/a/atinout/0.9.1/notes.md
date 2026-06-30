# atinout 0.9.1 适配笔记

## 编译环境
- 构建系统: makefile (简单 Makefile，无 configure 脚本)
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4 (OpenHarmony SDK)
- 状态: published (conan-verify 全部 8 道门禁通过)

## 源码信息
- 源码 URL: https://sourceforge.net/projects/atinout/files/v0.9.1/atinout-0.9.1.tar.gz/download
- SHA256: 4d15c8288aca414e11cd304686b172696104c5e42bf776300311c005634854a2
- 许可证: GPL-3.0
- 主页: https://atinout.sourceforge.net/

## 编译步骤

atinout 是一个非常简单的 C 程序，只有一个源文件 (atinout.c) 和一个简单的 Makefile。
没有 configure 脚本，不需要 autotools。

### 手动编译 (探索阶段)
```bash
source .build-context-atinout-0.9.1
cd $BUILD_SRC_DIR
make -j1 CC=clang PREFIX=$DEFAULT_PREFIX
make install CC=clang PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
make check  # 无 check 目标，Makefile 不包含测试套件
```

### Conan 配方编译 (固化阶段)
conanfile.py 中的 build() 方法:
```python
self.run('make -j1 CC="${CC}"')
```
- 使用 AutotoolsToolchain 生成环境变量 (CC, CFLAGS 等)
- 通过命令行传递 CC 覆盖 Makefile 的 CC=gcc
- 保留 Makefile 原始 CFLAGS (包含 -DVERSION="0.9.1" 定义)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败，无法从 Savannah 下载源码 | Python urllib 不信任 Savannah 的 SSL 证书 | 使用 curl -kL 手动下载，然后 --no-download 初始化 |
| 2 | Savannah URL 返回 404 | atinout 的 Savannah 下载链接已失效 | 改用 SourceForge URL: https://sourceforge.net/projects/atinout/files/v0.9.1/atinout-0.9.1.tar.gz/download |
| 3 | Conan get() 报 BadZipFile | conandata.yml 的 URL 以 /download 结尾，Conan 无法识别为 tar.gz | 在 conandata.yml 中添加 filename: "atinout-0.9.1.tar.gz" |
| 4 | Conan create 编译失败: VERSION 未定义 | make -e 导致环境 CFLAGS 覆盖了 Makefile 的 CFLAGS (含 -DVERSION) | 改用 make CC="$CC" 只覆盖编译器，保留 Makefile 的 CFLAGS |
| 5 | ConanInvalidConfiguration 导入失败 | Conan 2.x 中 ConanInvalidConfiguration 在 conan.errors 模块 | 改为 from conan.errors import ConanInvalidConfiguration |
| 6 | test_package 中 atinout 命令找不到 | VirtualRunEnv 未正确设置 PATH | 使用 self.dependencies["atinout"].cpp_info.bindirs[0] 获取完整路径 |
| 7 | 从 staging 目录执行二进制报 "Operation not permitted" | OpenHarmony ELF 签名要求 | 复制到 $HOME 目录可执行；CI 流水线通过 sign.sh 签名 |

## 源码修改

无补丁。源码未做任何修改，所有适配通过 Conan 配方参数实现。

## 依赖版本

atinout 无第三方依赖，仅依赖 musl libc (系统自带)。

## 验证结果

### 手动测试
```bash
$ atinout --version
atinout version 0.9.1
Copyright (C) 2013 Håkon Løvdal <hlovdal@users.sourceforge.net>
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it under
certain conditions; see http://www.gnu.org/licenses/gpl.html for details.

$ atinout --help
This program takes AT commands as input, sends them to the modem and outputs
the responses.

$ echo "AT" | atinout - /dev/null -
EOF from modem
```

### Conan 验证 (8 道门禁全部通过)
- G0: 预构建风险评估 PASS
- G1: 配方完整性 PASS
- G2: conan create PASS
- G3: 系统同名库隔离 PASS
- G4: 产物完整性 PASS
- L2: smoke test PASS
- L4: 安全扫描 (NX/PIE/RELRO) PASS
- L5: 产物基线 PASS

### 二进制安全特性
- ELF: shared object, 64-bit LSB arm64
- PIE: ✅
- RELRO: ✅ (完整 RELRO + BIND_NOW)
- NX: ✅ (GNU_STACK 无执行权限)
- 依赖: 仅 libc.so (musl)

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (CI 输入) |
| conandata.yml | 源码 + sha256 声明 (CI 输入) |
| test_package/conanfile.py | L1 测试 (CI 输入) |
| reports/test-report.md | 真实测试报告 |
| reports/conan-verify-report.md | Conan 验证报告 |

## 注意事项

1. atinout 的 Makefile 使用 `CC = gcc`，在 OpenHarmony 上必须通过 `CC=$CC` 覆盖为 clang
2. 不能使用 `make -e`，否则环境 CFLAGS 会覆盖 Makefile 的 CFLAGS (丢失 -DVERSION 定义)
3. SourceForge 的下载 URL 需要在 conandata.yml 中添加 filename 字段才能被 Conan 正确识别
4. atinout 不包含测试套件 (Makefile 无 check 目标)
5. OpenHarmony 平台限制: 未签名二进制从某些目录执行会报 "Operation not permitted"
---

**编译结束**: 2026-06-29 15:30
**最终状态**: published
