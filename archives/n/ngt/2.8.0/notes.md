# ngt 2.8.0 适配笔记

## 编译环境
- 构建系统: cmake (C++17, OpenMP + BLAS/LAPACK via OpenBLAS)
- 编译日期: 2026-09-04
- 编译器: OHOS SDK clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤
1. `conan create .`（profile ohos-aarch64；conan-verify 经加速镜像拉取官方源）
2. 配方关键设置（conanfile.py generate）：
   - `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（E092：CMake 不识别 OHOS 为 UNIX）
   - `NGT_MARCH_NATIVE_DISABLED=ON`（避免 -march=native）
   - `BLAS_LIBRARIES`/`LAPACK_LIBRARIES` 指向 openblas/0.3.34 的 libopenblas.so
3. 依赖：openblas/0.3.34（QBG 的 BLAS/LAPACK 符号源）+ libomp/15.0.4（OpenMP 运行时，E127）
4. 补丁 3 个见 patches/；source 内 make 由 cmake 驱动，LTO 开启（链接较慢）

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | MmapManager.cpp strerror_r 报 cannot initialize char* with int | glibc GNU 变体返回 char*，musl/OHOS 用 POSIX 变体返回 int，而编译默认定义 _GNU_SOURCE | 补丁 0001：忽略返回值，统一用 err_msg 缓冲（两变体都写入缓冲） |
| 2 | 链接 libngt.so 失败：-llapack/-lblas/-lstdc++fs not found | NGT 用裸名链接系统 LAPACK/BLAS，且无条件链 -lstdc++fs（GCC 专用） | 补丁 0002：改用 find_package(BLAS/LAPACK) 结果变量（OpenBLAS 全路径）；-lstdc++fs 仅 GNU 编译器链接 |
| 3 | conan build 阶段 cmake_symlink_library Permission denied | OHOS HMDFS/任务安全：python/conan 子进程无法创建符号链接（shell 可以）；NGT 设 VERSION/SOVERSION 触发 CMake 建 libngt.so.2 符号链接链 | 补丁 0003：去掉 VERSION/SOVERSION，产出无版本 libngt.so（OHOS loader 也拒绝经符号链接加载 .so，E316） |
| 4 | test_ngt 运行时报 Error loading shared library libomp.so | conan 测试二进制无 SDK llvm/lib RUNPATH，libomp.so 不在 LD_LIBRARY_PATH | requirements 增加 libomp/15.0.4，OpenMP 运行时随 conan 环境解析 |
| 5 | github.com 官方源直连不可达 | 网络仅 gitcode/cnb.cool 可达 | conan-verify 自动注入加速镜像（E017 预防，sha256 与官方一致 37c7538f...） |

## 源码修改
- patches/0001-mmapmanager-strerror-r-portable.patch
- patches/0002-ngt-cmakelists-link-blas-lapack-fixes.patch
- patches/0003-ngt-cmakelists-unversioned-shared-lib.patch

## 依赖版本
- openblas/0.3.34（ohpcd，BLAS+LAPACK 符号）
- libomp/15.0.4（ohpcd，OpenMP 运行时）
- Threads/OpenMP 由 OHOS SDK clang 工具链提供

## 验证结果
- conan-verify 8 门禁全 PASS（G0-G4 + L2/L4/L5）
- 上游无 ctest/make check 测试目标（tests/ 仅基准数据；实测 ctest -N = 0）
- 功能实测：ngt CLI 建 ANNG 索引 + L2 最近邻检索正确（查询自匹配 distance=0）
- test_package test_ngt：C++ API 建 200×16 ANNG 索引 + 搜索，1/1 PASS（0.09s）

## 注意事项
- 本仓库设备原生构建：OHOS SDK clang 位于 /data/service/hnp（设备固定布局）
- libngt.so 为无版本单文件（见补丁 0003 说明）
- 产物含 bin/ngt 与 bin/qbg 两个命令行工具 → 软件级 commands.json 已建（R38）
---

**编译结束**: 2026-09-04 16:59
**最终状态**: published

## 测试矩阵扩展（2026-09-04，MR #8234 增补）
- test_package 由单场景（test.cpp 11 断言）扩展为 9 个可执行 target / 167 断言：
  test_ngt(基线 11) / test_distance(L1/L2/Angle/Cosine, 32) /
  test_objecttype(Float/Uint8 + L2/Hamming, 24) / test_graph(ANNG/ONNG/IANNG, 24) /
  test_persist(save→rw/ro 重开, 21) / test_crud(remove 语义, 15) /
  test_batch(SearchQuery+SearchContainer 批量, 24) / test_property(get/set 往返, 11) /
  test_errors(异常路径, 5)。
- 数据确定性（固定种子）、自查询 exact self-match 断言；单测总时长 < 1s。
- conan-verify G2（conan create）实测 9/9 全 PASS（logs: reports/conan-create.log）。
- 上游 v2.8.0 tarball 再清点（R51）：仍无 ctest/make check/python 测试，仅 tests/ 基准数据与
  samples/ 示例（详见 test_package/MANIFEST.yml）。
