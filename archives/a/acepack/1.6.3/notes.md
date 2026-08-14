# acepack 1.6.3 OHOS 适配记录

## 库概况
- R 语言包：ACE（交替条件期望）与 AVAS（方差稳定化变换）回归变换工具
- License: MIT + file LICENSE（2025, 2007, Jerome H. Friedman / Shawn Garbett）
- NeedsCompilation: yes；17 个 Fortran 90 源（src/*.f90）+ init.c（C）
- 构建：R CMD INSTALL（无 configure/autotools/CMake），src/Makevars 定义编译规则
- 官方源：https://cran.r-project.org/src/contrib/acepack_1.6.3.tar.gz
- SHA-256（设备端实测）: 653093e308f0dea5ec2719985a01aff700d5795074b3f5239b34632bf45ebadf

## 依赖
- 直接：r-base/4.5.1（host；R 运行时与 R CMD INSTALL 驱动）；flang-ohos/20.1.0（tool；Fortran 编译）
- 可选：testthat、roxygen2（Suggests；testthat 依赖链过长未适配）
- 上游测试（方案二）：经 base R 兼容层 mock-testthat.R 在设备端运行 4 个上游测试文件，
  18/18 全部通过；P2 修复：expect_equal 改用绝对容差语义（上游 tol= 本意），消除
  ULP 级浮点差异误判；P1 修复：runner 按 .env$fail 返回非零退出码，失败穿透 CI 门禁（R9/R24）
- 备注：r-base/4.5.1 已合入官方基线（upstream/main 含 archives/r/r-base/4.5.1/）；其 Conan 制品暂未上传 ohpcd remote，本地 CI 用 --build=missing 从源码构建兜底，不阻塞构建与测试

## 关键适配点
1. r-base 制品 Makeconf 中 FC=false（打包时 _prepare_relocatable_runtime 清理构建缓存路径），
   导致 R CMD INSTALL 编译 .f90 时无 Fortran 编译器。
   关键发现：R CMD SHLIB 的 make 顺序为 -f Makevars -f Makeconf -f shlib.mk，
   Makeconf 后于 Makevars 处理，故 Makevars 中追加的 FC 赋值被 Makeconf 中 FC=false 覆盖。
   正确解法：用 R_MAKEVARS_SITE 环境变量指定 site Makevars 文件（flang-makevars.mk），
   该文件在 Makeconf 之后被 include，从而正确覆盖 FC=false。
   site Makevars 内容：FC/F77 指向 flang-ohos 包内 flang；FLIBS 指向 libFortran* 库。
2. FLIBS = -L<flang_lib> -lFortranRuntime -lFortranDecimal -lFortranCommon -lm
3. 环境注入：PATH 含 r-base bin 与 /data/service/hnp/bin；TMPDIR 指向设备 tmp；
   LD_LIBRARY_PATH 含 flang lib 与 r-home lib。
4. test_package：Rscript 真实调用 ace()/avas() 核心 API（禁止空壳 R34）；
   负向测试：包不在 R library 树时退出 66。

## 平台要点
- TMPDIR=/storage/Users/currentUser/tmp（鸿蒙 /tmp 只读）
- make 用 -j1（HMDFS 不支持 mkfifo/jobserver）
- AR/RANLIB 用绝对路径 /data/service/hnp/bin/llvm-ar、llvm-ranlib
- toybox 工具（gzip 等）仅支持短选项
