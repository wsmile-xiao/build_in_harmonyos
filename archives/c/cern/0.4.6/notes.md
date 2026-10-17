# cern 0.4.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-11
- 编译器: clang/clang++
- 状态: built（待真机预检回填实测证据）

## 上游信息
- 上游仓库：https://github.com/dpiparo/vdt
- 上游版本标签：v0.4.6
- 源码包：https://github.com/dpiparo/vdt/archive/refs/tags/v0.4.6.tar.gz
- SHA256：1820feae446780763ec8bbb60a0dbcf3ae1ee548bdd01415b1fb905fd4f90c54
- 许可证：LGPL-3.0-or-later
- 说明：任务名 cern 指 CERN VDT 向量数学库（Born and developed at CERN），Arch Linux 打包名为 cern-vdt 0.4.6-1，上游仓库为 dpiparo/vdt，当前最新标签即 v0.4.6，版本完全吻合。配方包名按任务要求取 cern，实际内容为 VDT。

## 编译步骤

1. 下载源码包并解压（conanfile source() 的 get，strip_root=True）。
2. 应用补丁 patches/0001-CMakeLists.txt.patch。
3. CMake 配置（generate() 注入）：
   ```bash
   cmake -DCMAKE_TOOLCHAIN_FILE=<OHOS toolchain> \
     -DBUILD_SHARED_LIBS=OFF \
     -DSSE=OFF -DNEON=OFF -DAVX=OFF -DAVX2=OFF -DFMA=OFF \
     -DDIAG=ON -DPRELOAD=OFF -DUSE_VC=OFF -DDEBUG=OFF
   ```
4. 编译：cmake --build .
5. 上游测试：build() 自动运行 source bin/ 下 12 个单元测试
   exp/log/sqrt/sin/cos/inv/tan/tanh/asin/acos/atan/atan2，
   输出 HMBS_UPSTREAM_TEST_RESULT 机器证据。
6. 安装：cmake --install .（头文件到 include/vdt，库 libvdt.a）。
7. 消费者测试：test_package 编译 test_cern.cpp 并运行 ./test_cern，
   输出 HMBS_TEST_PACKAGE_RESULT 机器证据。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认 SSE=ON 在 aarch64 报未知选项 -msse | 上游 x86 默认加 -msse，OHOS clang aarch64 不接受 | generate() 强制 SSE=OFF NEON=OFF AVX=OFF AVX2=OFF FMA=OFF，armv8 NEON 隐式可用，无需显式旗标 |
| 2 | DIAG 诊断程序链接 -lrt 在 OHOS 失败 | OHOS libc 无独立 librt，-lrt 找不到 | 补丁在 CMAKE_SYSTEM_NAME 为 HarmonyOS 时将 LIBTIMING 置空，仅影响链接，不改逻辑，未引入 __OHOS__ 宏 |
| 3 | src/ 需要 Python 生成签名 | src/CMakeLists find_package Python Interpreter | 依赖真机 python3（hmbs 注入 HMBS_PYTHON3/PATH），无需 conan 依赖 |
| 4 | 上游无 ctest 注册 | 未调 enable_testing/add_test，只有独立可执行文件 | build() 逐个 self.run 真实二进制并计数，数字来自实际执行，非硬编码 |

## 源码修改

- patches/0001-CMakeLists.txt.patch
  - 顶层 CMakeLists DIAG 段：HarmonyOS 时 LIBTIMING 置空（hunk 头修正为 -118,9 +118,14，原 -44,8 与包体不符导致 conan 报 Failed to parse patch）
  - progs/units/CMakeLists.txt：test_fcnPerformance 硬编码 rt 改为 ${LIBTIMING}，HarmonyOS 时随顶层置空，Linux 保持 -lrt
  - 未碰 C/C++ 源码，未引入平台宏，POSIX 兼容的 CMake 系统名判断

## 依赖版本

无外部运行依赖（纯 CMake + 头文件 + 小库）。构建时需要 python3（真机提供）。

## 验证结果

待 HMBS 真机预检回填。本地已做：
```bash
curl -sL https://github.com/dpiparo/vdt/archive/refs/tags/v0.4.6.tar.gz -o vdt-0.4.6.tar.gz
python -c "import hashlib; print(hashlib.sha256(open('vdt-0.4.6.tar.gz','rb').read()).hexdigest())"
# 输出 1820feae446780763ec8bbb60a0dbcf3ae1ee548bdd01415b1fb905fd4f90c54，与 conandata.yml 一致
tar tzf vdt-0.4.6.tar.gz | grep units  # 确认 12 个 *_test.cpp 存在
```

上游测试防假阳性说明：
- 12 个测试输出 printFuncDiff 非空才算执行（空输出视为失败计数）。
- test_cern.cpp 对标 libm（std::exp/sin/cos/log）做容差比对，
  故意改错任一容差即非零退出，harness 可捕获失败，非静默跳过。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，含上游 12 测试运行与证据标记 |
| conandata.yml | 官方 GitHub tag 源 + sha256 + 补丁声明 |
| test_package/ | test_cern.cpp（9 断言）+ CMakeLists + MANIFEST |
| manifest.yaml | 版本级构建元数据 |
| notes.md | 本文件 |

## 注意事项

- 包名 cern 按任务目录要求，实际为 CERN VDT，PR 正文已写明对应关系。
- 默认静态（shared=False），非系统同名库，无需 R26 强制静态之外的处理。
- 纯库，无 commands.json。
- 真机环境与官方 CI 同源，正文写“在 HarmonyOS aarch64 环境实测”而非内部真机地址。
