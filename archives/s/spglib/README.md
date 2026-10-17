# spglib

## 简介

Spglib 是用于晶体对称性分析的 C 语言库：输入单胞结构即可求解对称操作、
判定空间群类型、输出标准化晶胞与数据集 (`SpglibDataset`)，广泛用于材料
科学与第一性原理工具链。

## OHOS 适配

- C 核心零外部运行时依赖，无需系统补丁
- Fortran/Python/OpenMP 可选接口保持关闭，只交付 `Spglib::symspg` 主库
- `SPGLIB_WITH_TESTS=ON` 在构建中完整运行上游 ctest 套件
  (unit/integration/functional/package/example)
- 消费者测试以单原子简立方断言 Pm-3m (221)，覆盖版本/数据集/释放全链路

## 依赖

- 无

## 功能验证

```bash
# 消费者测试调用 spg_get_dataset / spg_free_dataset 真实 API
```

## 参考

- 官网: https://spglib.readthedocs.io/
- 上游仓库: https://github.com/spglib/spglib
