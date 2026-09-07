# cba 0.3.6 适配笔记

## 编译环境
- 构建系统: makefile（上游为纯 Makefile 工程，无 configure.ac / autotools）
- 编译日期: 2026-09-05
- 编译器: clang 15 / clang++（OHOS aarch64，armv8）
- 状态: built

## CLI-only 决策（W0）
上游 cbeam 0.3.6 同时含 CLI（`src/` → `cba`，核心求解器 `cbeam_class.cpp/h`）与
wxWidgets GUI（`src/gui/` → `cba-gtk`/wxCBA）。**源码中不存在 configure.ac /
--disable-wx 开关**（任务描述假设的 autotools 构建系统在真实 0.3.6 源码中不存在），
CLI 与 GUI 是在**顶层 Makefile 层分离**（分别递归 src/ 与 src/gui/）。Debian 侧同样
是分离构建。因此 CLI-only 的实现 = 配方只执行 `make -C src`，跳过 src/gui ——
零 wxWidgets 依赖（制品仓中 wxWidgets 3.2.x 已适配但无需引入）。

## 编译步骤
```bash
make -C src -j1 CXX=<clang++ 绝对路径> CXXFLAGS=-O2
# 产物 src/cba → 安装到 package bin/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 找不到编译器 | src/Makefile 硬编码 `CXX := c++`，CI 无 c++ 符号（仅有 clang++） | conanfile build() 在 make 命令行覆盖 CXX（命令行变量优先级高于 `:=`），编译器路径取自 Conan profile conf（R33） |
| 2 | 数值输出包络语义 | Mmax/Mmin/R 为"逐跨布置 × 荷载分项系数"的包络值（非全载静力值） | 新增测试只断言全载退化/极值工况（可解析独立复核的值），避开包络歧义 |

## 源码修改
无（零补丁，纯 Makefile 命令行参数适配）

## 依赖版本
无外部依赖（纯 libc++/标准库）

## 验证结果
```bash
# CLI 冒烟：readme 示例（两跨 5.8/4.2 HEA200）
# 特征 Mmin=-50.47 与解析 MB=-w(L1^3+L2^3)/(8(L1+L2))=-50.475 一致；
# 设计组合 1.35/1.5 → -70.67 与 -70.665 一致。
# 单跨 UDL Mmax=160.00=wL^2/8、R=80=wL/2、dmax=0.138≈5wL^4/384EI=0.1376
# test_package: 11 用例 / 55 断言（6 结构解析解比对 41 + 4 CLI 错误路径 8
#                + 1 -o/-p 输出/plot 一致性 6），全数通过
```

## 测试说明
上游无任何测试（三层证据：①tarball 树无 tests/ 目录；②Makefile 无
check/TESTS 目标；③无 configure.ac）。test_package 以 C++ harness 程序化构造
输入文件驱动 `cba -i/-o/-p`，比对立解析解与 CLI 输出、错误路径退出码。

## 交付物
- bin/cba（aarch64 OHOS CLI，静态结构求解）
- share/licenses/cba/licence.txt

## 注意事项
- cba 无 --version（无参数时打印 usage 并 exit 1）——CI L2 smoke 为 warn 不阻塞
- plot 文件 = 1 表头 + 1 空行 + nf*101 数据行
- 默认特征组合 = (1.0,1.0)，最小组合 = (1.0,0.0)（活载卸荷）；4 个 FACTORS
  可自定义卸荷系数
---

**编译结束**: 2026-09-05 14:03
**最终状态**: built
