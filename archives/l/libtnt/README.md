# libtnt

libtnt（**T**emplate **N**umerical **T**oolkit，NIST TNT）——NIST 开发的
C++ 科学计算数值模板库（Debian 打包名 libtnt，对应 libtnt-dev）。

## 简介

TNT 提供科学计算 C++ 的数值对象接口与参考实现：多维数组
（Array1D/2D/3D、Fortran 风格 1-based 数组）、CSR 稀疏矩阵只读视图、
数值工具函数（hypot）与计时器（Stopwatch），是 JAMA/C++ 线性代数包的
底层数组基础设施。1.2.6 为官方最终发布版（NIST 维护终止版），公有领域
（title 17 U.S.C. §105，SPDX: NIST-PD，声明内嵌每个头文件）。

## 主要特性

- Array1D/2D/3D：引用计数共享视图 + copy() 深拷贝，`operator[]`
  行指针风格访问（A[i][j]），T*/T**/T*** 裸指针衰减与既有 C 代码互通
- Fortran_Array1D/2D/3D：1-based 索引，与 Fortran 例程/列主序数据互操作
- Sparse_Matrix_CompRow：CSR 三数组格式只读视图（0-based）
- matmult 等 utils：矩阵乘/逐元素四则/流输出
- Vector/Matrix（deprecated）：pre-1.0 值语义容器，随包保留
- header-only：纯模板，零依赖（仅 C++ 标准库头）

## 构建

- 无构建系统：官方 zip 为 21 个 tnt*.h 扁平分发包，package() 直接
  拷贝 include/ + 从 tnt.h 提取 NIST 公共领域声明落盘 licenses/LICENSE
- 补丁 0001（bugfix）：Sparse_Matrix_CompRow 构造函数参数去 const，
  修复 tnt.h 在 clang 下 include 即编译失败的上游硬缺陷

## 版本

- 1.2.6（2026-09-16 适配）：真机 conan create 全绿，test_package
  38/38 断言（组件冒烟 32 + 消费者用例 6），详见 1.2.6/notes.md
