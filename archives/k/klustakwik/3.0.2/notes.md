# klustakwik 3.0.2 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 autotools/cmake/meson/configure）
- 编译日期: 2026-09-15
- 编译器: clang/clang++（OHOS 工具链，经 Conan conf 注入，R33）
- 状态: built

## 编译步骤

```bash
# 源码: SourceForge maskedKlustaKwik/KlustaKwik-3.0.2.bz2（官方源）
# 下载并解压后，直接调用上游 makefile：
make CC="<clang++ 路径>" -j1
# 产物: ./KlustaKwik（可执行文件）
```

- 无 configure 步骤；无外部依赖（纯标准 C/C++，stdio/stdlib/math/time/vector 等）。
- OHOS 上编译产物需 HNP binary-sign-tool 签名后才可执行（conanfile.py build() 中
  检测工具存在时自动签名）。
- 上游 makefile 硬编码 `CC = g++`，适配中由 Conan conf 的
  `tools.build:compiler_executables:cpp` 覆盖（R33，禁用 shell ${CC}）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 将 build_system 判定为 autotools | 项目无 configure，实际为纯 makefile | manifest 修正为 makefile，conan-init 重新生成 |
| 2 | OHOS 上未签名 ELF 不可执行 | 鸿蒙内核要求 ELF 带 .codesign 段 | build() 内检测 /data/service/hnp/bin/binary-sign-tool，存在时签名 |

## 源码修改

无补丁（patches 为空）。源码 100% 保持上游原样，仅通过 make 变量注入工具链。

## 依赖版本

- 无第三方依赖（C++ 标准库 + libm）

## 上游测试清点（R51 三步法 · 第一步）

**上游测试：0 个**

清点证据：
1. 官方 tarball（maskedKlustaKwik/KlustaKwik-3.0.2.bz2）解包后文件清单：
   `.cproject .project .pydevproject dan_changes.txt expected_output.txt
    expected_output_2.txt globalswitches.h gmon.out io.cpp klustakwik.cpp
    klustakwik.h linalg.cpp linalg.h log.cpp log.h makefile makefile~
    makeprofiletxt.bat numerics.h OldVersions/ parameters.cpp parameters.h
    precomputations.cpp profile.txt util.cpp util.h`
2. `makefile` 目标清单：`all` / `clean` / `native` / `install`，**无 check/test 目标**；
   `make -n check` 无对应规则。
3. 不存在 `tests/`、`test/` 目录；无任何测试源文件。
4. `expected_output.txt` / `expected_output_2.txt` 是作者在自备 `dantest`
   数据上的**参考运行日志**，tarball 内不含配套 `.fet`/`.mask` 输入数据，
   不可复现运行（R51 第三步申报上游确无测试时附此证据）。

## 验证结果
```bash
# 本地 macOS（默认 profile）构建验证
make CC="c++" -j1 && ./KlustaKwik  # 输出 Usage 说明编译与运行正常

# 合成数据真实聚类（200 点 4 特征、2 高斯簇）：
./KlustaKwik testdata 1 -MinClusters 2 -MaxClusters 5 \
    -MaxPossibleClusters 10 -nStarts 1 -RandomSeed 2304983 -MaxIter 500 -Verbose 0
# 输出 testdata.clu.1：201 行（1 行簇数头 + 200 行标签），恢复出 2 个簇

# Conan 本地验证
ohc-run.py conan-verify klustakwik 3.0.2
# CI: ohc-run.py conan-verify klustakwik 3.0.2 --profile ohos-aarch64
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Makefile 项目，application 类型） |
| conandata.yml | 官方源码 URL + SHA256 |
| test_package/ | L1 测试：5 项断言（二进制/架构/真实聚类/输出形状/聚类质量） |
| commands.json | CLI 工具声明（R38） |

## 注意事项

- 本库为科研 spike sorting 工具，仅标准 C/C++，无平台特定代码，OHOS 适配点
  集中在工具链注入（R33）与 ELF 签名。
- 上游无测试，PR 测试统计表按 R51 如实申报：上游 0 个，适配后 test_package
  5 项断言（含 aarch64 ELF 架构验证这一鸿蒙特有检查）。

## 发现与知识

- ✅ KlustaKwik 3.0.2 (MaskedKlustaKwik) 为纯 Makefile 构建的 C++ 命令行工具，无外部依赖，编译产物为可执行文件 KlustaKwik（ref: E540）
- ✅ 上游包内无测试框架与测试数据，expected_output*.txt 仅为作者参考运行日志，R51 清点如实申报 0 个上游测试（ref: E292）
- ✅ Makefile 包在 OHOS 交叉工具链下需显式注入 CC/CXX（conanfile.py 经 Conan conf 取 compiler_executables），产物需 binary-sign-tool 签名

## 对话记录

### 对话 #1
- 2026-09-15：完成 klustakwik 3.0.2 鸿蒙适配（纯 Makefile C++、零依赖）；R51 清点上游 0 测试；conanfile.py + test_package 5 断言就绪；W3 本地 CI 通过（L0/L1/L4/L5 PASS、L2 skip）；本机 default profile conan-verify 曾 G1-G4 全 PASS；ohos-aarch64 交叉验证依赖远程 OHOS CI（本机无 /data/service/hnp 工具链，未伪造结果）。
---

**编译结束**: 2026-09-16 01:09
**最终状态**: built
