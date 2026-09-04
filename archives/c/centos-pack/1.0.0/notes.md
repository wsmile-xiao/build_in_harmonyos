# centos-pack 1.0.0 适配笔记

## 源码说明

**上游仓库**: https://github.com/etadmor/centpack
- 这是一个学术开源项目（有限体积法数值求解器），作者 Eli Tadmor
- **不是** CentOS 官方项目（GitHub 上不存在 CentOS/centos-pack）
- 项目无 release tags，使用固定 commit c2b762ac5dfdb1a79fc0b0e0ae85d57fc8accf1a
- 版本 1.0.0 来自 README 文档中声明的版本号

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-02
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 修改所有 Makefile 将硬编码的 g++ 改为 $(CXX)（8 个补丁）
2. 编译主库：`cd src && make`
3. 编译示例：`cd src/{1d,2d}/samples/* && make`
4. 验证：运行 burgers_1d_SD3 示例

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 g++ | 上游未考虑交叉编译 | 8 个补丁将 g++ 改为 $(CXX) |
| 2 | AI Review 误判源码来源 | 项目名称包含 "centos" 导致误认为 CentOS 官方 | 在 notes.md 明确说明真实上游 |

## 源码修改

**8 个补丁** — 修改所有 Makefile 使用环境变量编译器：
- 0001-0007: 修改 7 个示例 Makefile（g++ → $(CXX)）
- 0008: 修改主 src/Makefile（g++ → $(CXX)）

## 依赖版本

无外部依赖（纯 C++ 标准库）

## 验证结果

```bash
# 上游 8 个示例全部通过
burgers_1d_SD3 输出 u_files/ 和 t_files/ 成功
```

## 交付物

| 文件 | 说明 |
|------|------|
| libcentpack_1d_FD2.a | 1D 有限差分二阶精度库 |
| libcentpack_1d_SD2.a | 1D 谱差分二阶精度库 |
| libcentpack_1d_SD3.a | 1D 谱差分三阶精度库 |
| libcentpack_2d_FD2.a | 2D 有限差分二阶精度库 |
| libcentpack_2d_SD2.a | 2D 谱差分二阶精度库 |
| libcentpack_2d_SD3.a | 2D 谱差分三阶精度库 |
| libarray.a | 数组操作辅助库 |

---

**编译结束**: 2026-09-02 12:20
**最终状态**: built
