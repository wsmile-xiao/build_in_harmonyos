# cute_c2 - Single-file 2D collision detection header

## 简介
cute_c2 是 Randy Gaul 的 cute_headers 单头文件库集合中的一员，
提供一个 C 头文件 `cute_c2.h`，实现 2D 碰撞检测例程（圆、胶囊、AABB、
射线、凸多边形之间的重叠测试与碰撞流形生成）。

## 特性
- 单文件头库，零依赖，纯 C99
- 布尔命中检测 + 碰撞流形生成（法线、深度、接触点）
- GJK（最近点对）、TOI（time of impact）扫掠、2D 凸包生成
- 定义 `CUTE_C2_IMPLEMENTATION` 后在一个编译单元中包含即可生成实现

## OHOS 适配状态
- bootstrap 阶段（版本 1.0.0）：官方仓库/版本锚定与源码校验值已核验，
  最小归档与配方骨架已建立；尚未进入 adapt 与编译验证。

## 来源
- 官方仓库: https://github.com/RandyGaul/cute_headers
- 1.0.0 锚定提交: 2ec5dce2310c（头文件内部版本 v1.0，2017-02-13 initial
  release；该提交时刻文件名为 tinyc2.h，2018-05-21 改名 cute_c2.h）
