# libblastrampoline

## 简介
动态 BLAS/LAPACK 符号转发层：导出全套 FORTRAN BLAS/LAPACK/LAPACKE 符号
（5384 个，含 `64_` 后缀的 ILP64 变体），运行时经 dlopen/dlsym 将调用转发
到真实后端库（OpenBLAS、BLIS、MKL 等）。Julia 生态的标准 BLAS 抽象层。

## OHOS 适配
- 构建系统: 纯 Makefile（src/Makefile），无 configure
- 无需补丁：HarmonyOS `uname` 走上游通用 Unix 分支
- musl 无 RTLD_DEEPBIND → 上游自动编译 deepbindless 路径
- dlopen/dlsym 由 libc.so 提供（musl 合并 libdl），无需 -ldl
- 详见 5.15.0/manifest.yaml

## 依赖
- 无链接期依赖（后端库由消费者在运行时加载）

## 功能验证
- 8/8 上游 C 测试通过（真实 openblas LP64 后端 + 可控 ILP64 fake 后端）
- 消费者测试 41 项断言：符号转发、后端切换、接口探测、错误路径、
  deepbindless 冲突语义（见 5.15.0/test_package/）

## 参考
- https://github.com/JuliaLinearAlgebra/libblastrampoline
