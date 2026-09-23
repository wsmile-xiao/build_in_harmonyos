# libmsym

## 简介
C library dealing with point group symmetry in molecules（分子点群对称性 C 库）：
点群判定、对称化、等价元素、子群枚举、特征标表、SALC/对称性轨道生成。

## OHOS 适配
- 构建系统: cmake（C99）
- 已适配版本: 0.2.3
- 详见 [0.2.3/notes.md](0.2.3/notes.md) 获取适配详情与实测判据

## 依赖
无外部依赖（仅链系统 `libm`；`system_libs = ["m"]` 已在 recipe 中声明）

## 功能验证
- `0.2.3/test_package/test_libmsym.c`：消费者视角真跑交付库，对 H2O(C2v)、NH3(C3v)、
  CH4(Td)、C6H6(D6h) 标准几何断言点群类型/群阶/各类对称操作数/特征标表维数/等价集，
  92 项断言全部通过（`conan create` 干净轮 `test_package` 段实测）
- 上游 v0.2.3 无任何测试入口（无 `test/` 目录、CMake 无 `enable_testing()`/CTest）；
  详见 `0.2.3/notes.md` 的「验证结果」段（`reports/` 被 `.gitignore` 覆盖，不入库）

## 参考
- 上游仓库: https://github.com/mcodev31/libmsym
- 点群理论依据: 各类点群的标准分子几何与群阶（C2v=4、C3v=6、Td=24、D6h=24）
