# libomp

## 简介
libomp 是 LLVM 项目的 OpenMP 运行时库，为 Clang 编译器提供 OpenMP 并行编程支持。

## OHOS 适配
- 构建系统为 CMake，使用 OPENMP_STANDALONE_BUILD=ON 独立构建
- HarmonyOS 不支持 pthread_cancel，需 undef KMP_CANCEL_THREADS（类似 Android）
- 官方源码包缺少 LLVM 公共 cmake 模块 ExtendPath.cmake，在 source() 中补充
- 禁用 libomptarget（OPENMP_ENABLE_LIBOMPTARGET=OFF）以避免 LLVM 依赖
- 禁用 OMPT 支持（LIBOMP_OMPT_SUPPORT=OFF）减少依赖

## 依赖
无外部依赖

## 功能验证
```bash
# 检查安装
ls $HOME/usr/local/lib/libomp*
```

## 参考
- [LLVM OpenMP](https://openmp.llvm.org)
- [E081: HarmonyOS pthread_cancel 缺失](../../knowledge/doc/E081.md)
