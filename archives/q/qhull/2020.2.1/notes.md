# qhull 2020.2.1 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libqhull.so，供 dlopen 及作依赖。

## 关键适配
- （填：系统识别 / umask / 子包 / zipfs / 签名等）

## 状态
built（CI conan create + test 通过）

## conan 化要点

重做原 2020.2：其产物无 SONAME（同 console_bridge 的问题）。本版 SONAME=libqhull_r.so.8.0，与上游 SOVERSION 8.0 一致，也与 coal 所链的名字一致。另：必须保留 BUILD_STATIC_LIBS=ON —— coal 要 find_package(Qhull COMPONENTS qhull_r qhullcpp)，而 qhullcpp 只有静态版。test_package 9 条凸包数值断言（体积/表面积/顶点数闭式解对账）。
