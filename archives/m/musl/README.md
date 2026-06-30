# musl

## 简介

musl是一个轻量级、简洁、符合标准的C标准库实现，专为静态链接设计，可作为glibc的替代方案。

## OHOS 适配

### 适配要点
- musl构建系统不支持`make check`测试套件
- 编译过程无需修改源码，configure直接通过
- 可作为OpenHarmony系统的C标准库替代方案

### 已知问题
- 无测试套件，无法自动验证功能完整性
- G4质量门禁报告有误（检测为无二进制文件，实际产物完整）

## 排除与替代

- 无不推荐安装的组件

## 依赖

### 编译依赖
- 无外部依赖（自包含C标准库）

### 运行依赖
- 无运行依赖

## 功能验证

```bash
# 编译产物验证
ls ~/usr/local/lib/libc.a          # 静态库 (2.6M)
ls ~/usr/local/lib/libc.so         # 共享库 (993K)
ls ~/usr/local/include/*.h         # C标准头文件

# 运行时验证（需链接测试程序）
# musl提供完整的C标准库接口
```

## 参考

- 官网: https://musl.libc.org/
- 源码: https://musl.libc.org/releases/
- 文档: https://musl.libc.org/manual.html