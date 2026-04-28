# dtc (Device Tree Compiler)

## 简介
dtc 是设备树编译器，用于处理设备树源文件（DTS）和二进制文件（DTB）。

## OHOS 适配
- 使用 Makefile 构建，非完整 autotools
- clang 不支持 GCC 特有警告选项 `-Wsuggest-attribute=format`，需从 Makefile 移除
- 动态链接工具需设置 LD_LIBRARY_PATH

## 排除与替代
无。

## 依赖
无外部依赖。

## 功能验证
```bash
dtc --version  # 显示 Version: DTC 1.7.2
```

## 参考
- 官网: https://devicetree.org/
