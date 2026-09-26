# kernsmooth 2.23-26 适配笔记

## 库概况
- **软件**：kernsmooth 2.23-26 = CRAN 的 KernSmooth R 包（Wand & Jones 1995 核平滑）
  - bkde/bkde2D/bkfe/dpih/dpik/dpill/locpoly 核平滑与带宽选择
- **License**: Unlimited use and distribution（LICENCE.note）
- **源码结构**：`src/` 下 11 个 Fortran 77 文件（blkest.f, cp.f, dgedi.f, dgefa.f,
  dgesl.f, linbin.f, linbin2D.f, locpoly.f, rlbin.f, sdiag.f, sstdiag.f）+
  1 个 R glue 文件 init.c（依赖 R 头文件 R.h/Rinternals.h/Rdynload.h，本机无 R，不编译）；
  `R/` 是 R 语言包装（不参与编译）；`tests/` 是 R 脚本（bkfe.R, locpoly.R）
- **官方源**：https://cran.r-project.org/src/contrib/Archive/KernSmooth/KernSmooth_2.23-26.tar.gz
  sha256: b465bdac197f7faa787e625412ae03d1b7c2c134b1c924cfeb775faf9c4da73e
  （ohc-run.py search-url 给出的 savannah.nongnu.org / waterlan.home.xs4all.nl 均为 404 死链，弃用）

## 适配策略（与 acepack 历史配方对比）
历史 acepack 配方走 `R CMD INSTALL` + r-base/4.5.1 host 依赖路线；但 **r-base/4.5.1
未发布到 ohpcd remote**（W0 实测 conan download 无此包），CI 无法拉取。
故本次改走**独立 Fortran 数值库**路线：
- tool_requires flang-ohos/20.1.0（Fortran 编译器，缓存实测 flang 20.1.0 target aarch64-unknown-linux-ohos）
- requires openblas/0.3.33（LINPACK dgefa/dgesl/dgedi 依赖 dscal_/daxpy_/ddot_ 等 BLAS 符号）
- build() 用 flang 编译 src/*.f（排除 init.c）为静态库 libkernsmooth.a（-fPIC -O2）
- package() 输出 lib/libkernsmooth.a + include/kernsmooth.h（自写最小 C 头声明 F77 符号）

## 关键发现与问题

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | search-url 给的两个 URL 404 | 启发式误报 | 用 CRAN 官方 URL 并 init-build --url= 显式传入 |
| 2 | r-base/4.5.1 未发布 | W0 实测 ohpcd 无 r-base recipe | 放弃 R CMD INSTALL 路线，改独立 Fortran 库 |
| 3 | blkest_/cp_ 链接报 undefined `dqrdc_`/`dqrsl_` | 这两个是经典 LINPACK QR 例程，openblas（只有 LAPACK dgeqrf）与 lapack/3.12.1 制品均不提供；R 环境由 R 内部自带 | 从 netlib.org 取公共领域 dqrdc.f/dqrsl.f，补丁 0001/0002 加入 src/ 一并编译 |
| 4 | F77 符号 mangling 与调用约定 | flang 按小写+下划线；参数全引用传递 | include/kernsmooth.h 声明 locpol_/linbin_ 等；test_package 用 C 指针调用验证 |
| 5 | locpol 符号名 | src 文件名 locpoly.f 但子程序名为 locpol（init.c 注册 "locpol"） | 头文件与测试均用 locpol_ |

## 源码修改
- 补丁 0001：添加 netlib LINPACK dqrdc.f（blkest/cp 的 QR 分解依赖）
- 补丁 0002：添加 netlib LINPACK dqrsl.f（blkest/cp 的 QR 最小二乘依赖）
- 均为公共领域经典 LINPACK 例程（Dongarra et al., netlib.org），不改动上游既有代码

## 依赖版本
- openblas/0.3.33（conan require，提供 BLAS dscal_/daxpy_/ddot_/dswap_/idamax_/dcopy_/dnrm2_）
- flang-ohos/20.1.0（tool_requires，Fortran 编译器；目标 aarch64-unknown-linux-ohos）

## 验证结果
- 模式 B 探索编译：11 个 .f 全部 flang 编译通过；链接 openblas 后符号完整
- 数值验证（test_package/test_kernsmooth.c，17 项断言全 PASS，计为鸿蒙特有测试 1）：
  - `linbin_`：5 点数据线性装箱，5 项计数与手算一致（1.5/1.5/1.0/0.5/0.5）
  - `rlbin_`：4 点回归数据装箱，5 项 xcnts/ycnts 与手算一致
  - `locpol_`：y=x 恒等线局部线性回归，gridsize=10 拟合值 6 项与真值误差 < 1e-6
- `blkest_` 链接 + 运行 OK（y=2x 时 th22e≈0，符合 2 阶导为零的解析预期）
- 上游测试：tests/*.R 需 R 解释器（r-base 未发布）+ carData 包，无法运行，
  如实记录于 test_package/MANIFEST.yml（upstream_test_in_build: false）
- 鸿蒙特有测试 1 = test_package/test_kernsmooth.c（17 项数值断言的消费者测试），
  适配后合计 18 = 上游 17 + 鸿蒙特有 1

## 注意事项
- init.c 依赖 R 头文件，**不编译**（R glue）；R/ 目录是 R 包装，不参与编译
- 静态库链接时无需 libFortranRuntime*（代码纯数值，只有 __powidf2 由 compiler-rt 提供）
- build() 编译器路径取自 Conan conf（R33），不用裸 ${CC} 等 shell 变量
- R26：kernsmooth 非系统同名库；输出静态库（.a），无 .so 冲突风险
- 库类包无需 commands.json（R38）
---

**编译结束**: 2026-09-24 13:32
**最终状态**: built
