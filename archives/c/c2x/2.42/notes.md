# c2x 2.42 适配笔记

## 编译环境
- 构建系统: makefile（顶层 Makefile，无 configure，无 install 目标）
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4（OHOS aarch64 原生工具链）
- 状态: built

## 编译步骤

```bash
make -j1 CC=clang DEFS= CPPFLAGS=-I. LDFLAGS= LIBS=   # 产物 c2x
```

- Makefile 硬赋值 `CC=gcc`、`CFLAGS=... $(DEFS)`、`LDFLAGS=-L.`、`LIBS=-lsymspg`，
  全部以 make 命令行变量覆盖（R33：CC 取自 Conan conf compiler_executables）。
- `DEFS= LDFLAGS= LIBS=` 即上游 Makefile 注释文档化的 no-SPGLIB 配置。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 spglib 构建编译失败：band_plot.c:105 `use of undeclared identifier 'j'` | 上游 #else（无 SPGLIB）分支腐烂：bands_plot() 用了只在该分支出现的循环变量 j 但从未声明（SPGLIB 路径不用 j，长期无人编译此分支） | 1 行声明补丁 `0001-band_plot.c.patch`（int 声明加 j），平台无关、非平台宏（R8 合规） |
| 2 | spglib 依赖未发布 | ohpcd 制品仓 conan download 实测 0 条 spglib 配方，归档树也无 | 采用上游文档化的 no-SPGLIB 配置先行发布；spglib 留作独立适配任务，之后可出带 spglib 的版本 |
| 3 | c2x.org.uk 裸域 SSL 证书主机名不匹配 | 证书仅覆盖 www 子域 | conandata 使用 `https://www.c2x.org.uk/downloads/c2x_2.42.tgz`（同一官方站点） |

## 源码修改

| 补丁 | 内容 | 原因 |
|------|------|------|
| patches/0001-band_plot.c.patch | bands_plot() 声明行 `int i,ik,...` → `int i,ik,j,...`（+1/-1） | 无 SPGLIB 分支编译失败，平台无关的上游 bug 修复 |

## 依赖版本

无（no-SPGLIB 配置；仅 libc + libm，-lm 由链接规则自带）。

## 测试统计（四口径）

| 口径 | 数量 | 说明 |
|------|------|------|
| 上游源码静态声明 | 1 | test_parser.c（带编译说明 `gcc test_parser.c parse.c -lm` 的独立测试程序，未接入 Makefile） |
| 上游套件实际执行 | 1 | 设备实测：`echo '1+2*3' \| ./test_parser` → `Final result: 7.000000`，退出码 0 |
| 跳过/未执行 | 0 | 无 |
| 新增 test_package 消费者测试 | 5 | test_c2x.py：binary 存在、-h 用法、无参数优雅报错、-V 版本与构建标识、CASTEP .cell→XSF 真实转换（CRYSTAL/PRIMVEC/PRIMCOORD/Si/5.43 断言） |

## 验证结果

```bash
./c2x -V                    # c2x version 2.42 / Not linked with spglib，退出码 0
./c2x -h                    # 完整用法，退出码 0
./c2x                       # Aborting: no input file specified. 退出码非 0（优雅错误）
./c2x si.cell si.xsf        # 真实转换，XSF 含 CRYSTAL/PRIMVEC/双 Si 原子/5.43 晶格
```

## 交付物

| 文件 | 说明 |
|------|------|
| c2x | 结构格式转换/分析工具（约 1.4 MB，GPL-3.0+） |

## 注意事项

- 官网文案称 "2.42a"（捆绑 spglib 2.0.2 的组合命名），源码 `C2XSF_VER "2.42"`，包版本 2.42 与源码一致。
- 已知限制：no-SPGLIB 配置下 `--bravais`/`--symmetry`/原胞求取等对称性功能不可用；`-V` 输出 `Not linked with spglib` 如实反映。spglib 适配发布后可跟进带 spglib 版本。
- 版本申报：平台任务号 #6172 版本字段为 2.42.a（Debian 重打包命名），实际上游与包版本为 2.42，PR 中如实说明。
---

**编译结束**: 2026-09-06 02:42
**最终状态**: built
