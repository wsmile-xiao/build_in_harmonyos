# DRAFT-icu-76.1-ohos-minimal-icucross-stub — ICU `--with-cross-build` 最小 stub 满足法

> **Contributor**: pc1-10 | **Status**: VERIFIED DRAFT | **Updated**: 2026-09-16
> **Source event**: icu 76.1 HarmonyOS PC adaptation, PR #8988

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终分类由知识库维护者和赛事评审决定。

## 适用场景

ICU（含 76.x / 77 / 78）在 HarmonyOS PC（aarch64）上以交叉编译方式构建，configure
检测到 `--host=aarch64-unknown-linux-ohos` 与 `--build=x86_64-unknown-linux-gnu`
不同，进入 `cross_compiling=yes` 后无条件要求 `--with-cross-build` 指向既有 ICU
构建树，否则中断：

```text
*** Configure: Cross compiling but no --with-cross-build ***
```

## 根因

ICU 的自举式（bootstrap）数据构建链：`icupkg`/`pkgdata`/`genccode` 必须在构建宿主
上运行以生成 `libicudata` 数据，而交叉编译时目标机上无法直接运行刚编译的宿主工具。
因此 configure 在交叉模式强制要求一个"已存在的构建树"以复用其宿主工具。HarmonyOS
CI 没有现成的 x86_64 侧 ICU 构建树，完整构建一棵树成本翻倍且与 SOURCE 长度无关。

## 方案

在 conan 构建目录内创建**最小 stub**，仅满足 configure 的存在性校验，不提供完整
构建树：

1. `config/icucross.mk`：写入 configure 实际读取的少量变量
   （`ICU_CROSS_BUILDROOT`、`U_IS_BIG_ENDIAN=0`、`U_HAVE_ATOMIC=1`、
   `U_HAVE_STRTOD_L=0`、`U_HAVE_XLOCALE_H=0`）。
2. `config/icucross.inc`：从源码自身 `config/mh-linux` 拷贝，追加
   `GENCCODE_ASSEMBLY_TYPE = -a gcc`（genccode 生成 C 汇编而非平台特定格式）。
3. 测试构建（`make check` / testdata）额外把已构建的
   `tools/gentest/gentest` 拷入 `<stub>/tools/gentest/`，使 `test.icu` 生成可运行。

该方案在本任务实测：`configure` 通过 → `make -j1` 完整成功（`libicudata.a` 31.9MB
静态数据、`libicui18n.a` 10MB、`libicuuc.a` 4.9MB）→ 消费者测试与鸿蒙专项测试均通过。

## 验证命令

```bash
grep -E "Cross compiling but no --with-cross-build|configuring ICU" config.log  # 不应出现
test -f <build>/icu-cross-stub/config/icucross.mk
test -f <build>/icu-cross-stub/config/icucross.inc
make -j1   # 数据打包步骤必须成功产出 libicudata.a
```

## 适用边界与反例

- 适用：ICU 系列（75+ 同 configure 逻辑）、其他在交叉模式下硬要求
  `--with-*-build` 宿主树指针的 autotools 库。
- 反例：无需 `--with-cross-build` 的普通 autotools 库（stub 无意义）；
  若 configure 校验真实执行 stub 内容（非仅存在性检查），需回退到真实宿主
  工具树。
- 禁止：以删除 `--host/--build` 三元组绕过交叉检测——会回到 E064 conftest
  执行崩溃路径并丢失目标平台特性检测。

## 关系

- similar_to: E176（ICU 平台适配，同库不同因）、
  DRAFT-gnustep-gui-ohos-autoconf-cross-probe（同交叉模式触发面）
- conflicts_with: E205 的 "Never use --build/--host" 仅针对 config.guess 缺失
  detection 的绕过；本方案在三元组已正确区分 host/build 后满足 configure 参数
  校验，不冲突
- prerequisite_of: 无；caused_by: 无