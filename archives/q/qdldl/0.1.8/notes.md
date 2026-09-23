# qdldl 0.1.8 适配笔记

## 编译环境
- 构建系统: cmake (CMake 4.1.2)
- 编译日期: 2026-09-04
- 编译器: clang/clang++ 15.0.4 (native OHOS aarch64)
- 状态: built

## 编译步骤
1. 官方源码下载并核验：URL https://github.com/osqp/qdldl/archive/refs/tags/v0.1.8.tar.gz
   - SHA256: ecf113fd6ad8714f16289eb4d5f4d8b27842b6775b978c39def5913f983f6daa
   - GitHub tag v0.1.8 → commit 138fdac58b9cd1c4137ff1b99152c8108a6cff5b；源码目录内 QDLDL_VERSION=0.1.8
2. `ohc-run.py init-build qdldl 0.1.8 --url=<官方URL>`（预置已核验 tarball 到 $TMPDIR/builds 缓存后执行）
3. 探索编译（源码 .work 目录，QDLDL_UNITTESTS=ON 以启用上游测试）：
   ```bash
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DQDLDL_UNITTESTS=ON \
         -DQDLDL_BUILD_DEMO_EXE=ON -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
   cmake --build build -j2
   ```
   → 零错误一次通过，产物 build/out/{libqdldl.a,libqdldl.so,qdldl_example,qdldl_tester}
4. 上游测试：
   ```bash
   ctest --test-dir build --output-on-failure        # 1/1 Passed (tester)
   ./build/out/qdldl_tester                          # ALL TESTS PASSED, Tests run: 9
   ```
   → 9/9 通过（test_basic, test_identity, test_rank_deficient, test_singleton,
   test_sym_structure, test_tril_structure, test_two_by_two, test_zero_on_diag, test_osqp_kkt），
   0 失败 0 跳过。详见 reports/test-report.md
5. staging 安装验证：`cmake --install build --prefix $TEST_PREFIX` → lib/libqdldl.{a,so} +
   include/qdldl/{qdldl.h,qdldl_types.h,qdldl_version.h} + lib/cmake/qdldl/* 均正确
6. `ohc-run.py conan-init qdldl 0.1.8` 生成配方，随后人工完善（见下）
7. `conan create` / `ohc-run.py conan-verify` 验证配方可复现

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 阶段 urllib 下载 GitHub tarball 报 "Remote end closed connection without response" | 该通道瞬时网络异常（curl 与 python requests 均可正常下载；重试即恢复） | 用 curl 预下载官方 tarball 并核验 SHA256 后预置 $TMPDIR/builds 缓存，init-build 命中缓存跳过下载 |
| 2 | 构建时警告 "make: jobserver mkfifo ... Operation not permitted" | OHOS 受限 FS 不支持 make jobserver fifo | 平台限制，非阻塞；cmake --build -j2 实际完成（警告无害） |
| 3 | 构建时提示 "System is unknown to cmake ... Platform/HarmonyOS"、"/proc/meminfo" 解析警告 | CMake 上游未内置 HarmonyOS 平台定义 | 无害告警；clang 编译器探测与编译均正常，不阻塞 |
| 4 | conan-init 模板把构建系统猜成 autotools（URL 不含 cmake 字样） | init_build 基于 URL 启发式猜测 | 版本级 manifest build.system 手工改为 cmake 后 conan-init 正确选用 cmake 模板 |
| 5 | conan-init 生成的 test_package/test.c 为空壳（仅 printf） | 生成器模板为通用占位 | 重写 test.c 真实调用 QDLDL_etree/QDLDL_factor/QDLDL_solve 完成 2x2 SPD 分解+求解并与解析解比对（7 项断言，实测通过）；test() 改为 self.run 直接运行二进制 |

## 源码修改
无。qdldl 0.1.8 为纯 C 自包含库，OHOS aarch64 上未修改任何上游源码，无补丁（patches/ 为空）。

## 依赖版本
- 无第三方依赖（编译期仅需 clang + make + cmake）

## 验证结果
- 探索编译：零错误（详见 qdldl-logs/build-configure.log、build-make.log）
- 上游测试：qdldl_tester 9/9 通过（ctest tester 1/1 Passed）
- 消费者 smoke：test_package/test.c 7/7 断言通过
- conan create / conan-verify：见 reports/ 与 .ci-result.json

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（CMake，shared 选项映射 QDLDL_BUILD_*_LIB） |
| conandata.yml | 官方源码 URL + SHA256 |
| test_package/ | 消费者测试（真实调用 qdldl API） |
| MANIFEST.yml | 上游测试声明 |

## 注意事项
- 库类型包（libqdldl.a/.so + 头文件），无可执行产物，按 R38 不需要 commands.json。
- qdldl 是 osqp 的下游依赖；若后续适配 osqp，需先发布 qdldl/0.1.8（R36 依赖发布顺序）。
---

**编译结束**: 2026-09-04 19:15
**最终状态**: built
