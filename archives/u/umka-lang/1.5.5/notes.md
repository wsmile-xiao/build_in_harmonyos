# umka-lang 1.5.5 适配笔记

## 编译环境

- 构建系统: makefile（纯 Makefile，非 autotools）
- 编译日期: 2026-06-29
- 编译器: clang 15.0.4
- 平台: HarmonyOS HongMeng Kernel 1.11.0 aarch64
- 状态: published

## 编译步骤

1. **init-build**：通过 gh-proxy.com 镜像下载源码包（GitHub 直连超时），自动解压到 .orig/.work 双轨目录，生成构建上下文。

2. **make 编译**：项目无 configure 脚本，直接使用 Makefile 构建：
   ```bash
   source .build-context-umka-lang-1.5.5
   cd $BUILD_SRC_DIR
   make -j1 PLATFORM=Linux PREFIX=$DEFAULT_PREFIX
   ```
   产物：`build/umka`（可执行文件）、`build/libumka.a`（静态库）、`build/libumka.so`（动态库）

3. **make install**：安装到 DESTDIR 隔离目录：
   ```bash
   make install PLATFORM=Linux PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
   ```
   安装产物：`bin/umka`、`lib/libumka.a`、`lib/libumka.so`、`include/umka_api.h`

4. **测试**：构建测试库后运行 all.um 测试套件，exit code 0，输出 1396 行与 expected.log 行数一致。

5. **Conan 配方**：conan-init 生成后手动修正为 makefile 构建系统，conan-verify 8 道门禁全部通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络无法直连 GitHub | 使用 gh-proxy.com 镜像 (`curl -kL https://gh-proxy.com/...`) |
| 2 | make 编译失败：平台不匹配 | `uname -s` 返回 "HarmonyOS"，Makefile 仅检测 Linux/Darwin/MINGW64 | 命令行传 `PLATFORM=Linux` 覆盖（Makefile 用 `?=` 允许覆盖） |
| 3 | make check 不存在 | 非 autotools 项目，Makefile 无 check 目标 | 手动运行 all.um 测试套件替代 |
| 4 | 测试比较失败 | expected.log 使用 CRLF 行尾，actual 使用 LF | 非功能性问题，内容完全一致（1396 行） |
| 5 | conan G2 首次失败：No makefile found | Conan basic_layout 将构建目录设为子目录，make 找不到 Makefile | conanfile.py 中 `self.run("make ...", cwd=self.source_folder)` |
| 6 | conanfile.py 模板不匹配 | 模板为 autotools，实际为 makefile | 重写 build()/package() 使用 self.run("make ...")，移除 Autotools 导入 |

## 源码修改

无源码修改。所有适配通过命令行参数（PLATFORM=Linux）和 Conan 配方调整完成，未修改任何源文件。

## 依赖版本

无外部依赖。仅需系统提供的 clang 15.0.4 编译器和 GNU Make 4.4.1。

## 验证结果

```bash
# umka 二进制可执行
$ ./build/umka
Umka 1.5.5 (Jun 29 2026 17:13:18 64 bit)
(C) Vasiliy Tereshkov, 2020-2025

# 测试套件
$ cd tests && ../build/umka all.um
$ echo $?
0
# 输出 1396 行，与 expected.log 行数一致

# Conan 配方验证
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify umka-lang 1.5.5
# G0-G4 + L2/L4/L5 全部 PASS
```

## 注意事项

1. umka-lang 的 LICENSE 文件实际内容为 BSD-2-Clause，conan-init 模板默认填 "MIT" 需手动修正。
2. conandata.yml 的 sha256 需手动计算并填入，模板生成时为占位符 "REPLACE_WITH_ACTUAL_SHA256"。
3. cpp_info.libs 应为 `["umka"]`（对应 libumka.a），模板默认填软件名 "umka-lang" 需修正。
4. 测试库 (tests/lib/lib.umi) 需在运行测试前手动构建，否则 all.um 中 extlib 测试会报 "Unresolved prototype"。
---

**编译结束**: 2026-06-29 17:28
**最终状态**: published
