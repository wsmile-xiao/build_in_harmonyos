# 内置 GoogleTest 的构建后发现也需要完整运行环境

本次查重完成、待主编审核草稿。通用触发特征是共享库配置下 `cmake --build` 已链接测试程序，但 `GoogleTestAddTests.cmake` 随即失败，首先报告 `libgtest_main.so` / `libgtest.so` 加载失败，其后的 testing 符号缺失是次生现象。

全局 BUILD_SHARED_LIBS 传播到内置 GoogleTest，产生 build/lib 中的共享测试库。默认 gtest_discover_tests 在 post-build 阶段执行；仅在后续 ctest 命令设置环境并不能覆盖这个阶段。外部依赖的 Conan VirtualRunEnv 不包含项目自己的内置测试库。

修复应在 CMake.build 之前把本任务的被测库目录和 bundled GoogleTest 输出目录加入 LD_LIBRARY_PATH，并保留外部依赖环境。不要停用 GoogleTest、删除测试或修改系统加载器路径。路径应从当前 build_folder 导出，不能硬编码缓存键。此方法不解决 ABI 不兼容、错误 SONAME、安装后签名失效等独立问题。

## 本次实证

Chromaprint 1.6.1 的第一次原生 Conan 构建失败于 post-build discovery，缺少 libgtest_main.so.1.16.0/libgtest.so.1.16.0。加入 build/lib 后，第二次完整 99/99 上游测试通过，但安装包消费者仍失败；因此 discovery 修复没有被误报为配方全部通过。

第二次回读证明安装目录、SONAME 别名与 Conan LD_LIBRARY_PATH 正确；CMake 安装日志另显示对已签名库执行 RPATH 重写。第三次设置 CMAKE_SKIP_RPATH=ON，保留 Conan 提供的运行时路径，最终原生 Conan create RC=0、99/99 上游测试、消费者 26 个断言及真实音频指纹通过。该安装问题属于已有签名知识的边界验证，不是本条的核心新增结论。

有效事务 chromaprint-conan-20261011T0544Z-r3；候选 SHA-256 40fdb720cff04c4c953457e4908adba047917f319693acda1a091814af9b5feb，日志 SHA-256 a8f27842d52a091f6aca6a8d4d69f7ede1c6d67c0530c2a5b88dfbd2e76f6493；完整 12 阶段及 release/postrelease PASS。日志与回执保存在本任务 evidence/chromaprint-conan-r3.*。

当前标准配方又通过正式 `chromaprint-finish-20261011-r2` 的 conan-verify 和 finish W3 本地 CI，99/99、1/1消费者（26断言、75指纹项），12阶段释放完整；W3原始日志SHA-256 `04fe2263282de7a877835981632112030a915d6845890a9408df2bf042dd185b`。总finish RC1为旧后置readiness/staging，不能冒充全流程PASS或比赛worker CI。

查重已覆盖 graph/drafts/doc/operations。E332 是离线独立 runner 选择，其他命中关于用例分母、交叉 PRE_TEST、内存或CTest子目录，与本条内置共享GTest的原生构建后加载路径机制不同。静态 GoogleTest、不使用 post-build discovery 或已有项目内测试库 RPATH 的配置不一定需要此处路径覆盖。
