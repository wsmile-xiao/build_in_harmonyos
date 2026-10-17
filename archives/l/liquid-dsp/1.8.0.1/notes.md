# liquid-dsp 1.8.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-16
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 真机）
- 状态: built（1.8.0 已发布，按 R37 递增修复版本）

## 编译步骤

```bash
tar xzf liquid-dsp-1.8.0.tar.gz
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_EXAMPLES=OFF -DBUILD_AUTOTESTS=ON -DBUILD_BENCHMARKS=OFF \
    -DBUILD_SHARED_LIBS=OFF -DBUILD_STATIC_LIBS=ON -DFIND_FFTW=OFF \
    -DCMAKE_INSTALL_PREFIX=<prefix>
make -j$(nproc)
make install
```

configure 结果：NEON=Yes（aarch64 自动启用）、SSE/AVX/AVX512/AltiVec=No、Threads=Yes、FFTW=No。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 静态包安装后的 `find_package(liquid)` 失败 | 上游 static-only 构建重命名 `LIBNAME`，生成的 Config 与 Targets 文件名不一致 | 应用 `0001-cmakelists-static-config.patch`，保持 CMake 包配置命名一致 |
| 2 | 已发布的 1.8.0 配方未在 CI 执行 autotest | `BUILD_AUTOTESTS=OFF` 且 `build()` 未调用 CTest | 新增 1.8.0.1，启用 `BUILD_AUTOTESTS` 并调用 `cmake.test()` |
| 3 | 修改 1.8.0 被 R37 拒绝 | 1.8.0 已发布且配方哈希不同 | 保持 1.8.0 不变，新增修订版本 1.8.0.1 |
| 4 | 裸 SSH runner 报 `cmake: inaccessible or not found` | 非交互 shell 未加载 HNP CMake/Ninja 路径 | 仅在隔离 runner 中 prepend HNP CMake/Ninja PATH，不把设备路径写入配方 |
| 5 | Conan 2 拒绝无 `shared` 选项的 `package_type="library"` | Conan 要求通用 library 声明 shared 选项 | 声明唯一允许值 `shared=False`；保留仓库类型规范且不暴露 shared 构建合同 |

## B 类知识库扩展候选

本库的 static-only 导出问题已抽象为通用 E327 draft：CMake 的 target 名、磁盘制品名与
供 `find_package()` 使用的逻辑包身份必须分离，变体分支不得修改后续用于
Config/Targets/install export 的包名。

- 草稿：`knowledge/drafts/E327-draft-D220.{kv,md}`
- 真机对照：`xuguowei-liquid-dsp-issue-2206-path-b-evidence-r3-20260815-225009-42915`，exit 0
- 去重：E216 是 CMakeDeps 组件传播；E278 是条件目标缺失后的 `-l` 退化，均非安装导出身份漂移
- 新增价值：旧 1.8.0 报告已有本库补丁；本次新增同源 before/after 证据与可迁移知识结构，不把旧补丁包装为新发现
- 完整证据：`reports/knowledge-expansion-evidence.md`

## 源码修改

应用 `0001-cmakelists-static-config.patch`。该补丁只修复 static-only 安装时
`liquidConfig.cmake` 与 Targets 文件的命名一致性，不修改 DSP 源码或测试。

## 依赖版本

无外部编译依赖。可选 FFTW 加速（fftw3f）已关闭，使用 liquid 内置 FFT 实现；
制品仓 cnb 中已有 fftw3f/3.3.9、3.3.9.1、3.3.10 可供后续按需启用。

## 验证结果

```text
1/1 Test #1: autotest ......................... Passed 60.41 sec
100% tests passed, 0 tests failed out of 1
```

- Shadow CI run: `xuguowei-liquid-dsp-liquid-dsp-issue-2206-shadow-r8r2-d1b4882a00-20260816-001734-29564`
- 被测代码提交: `d1b4882a00e3`
- 被测归档 SHA256: `426dfb52d71c2df908895998605bb6afcc38c5902218f81f831ac030935a35ef`
- Shadow CI 时间: 2026-08-16 00:17:34 至 00:22:15 +0800
- runner: heavy + `--try-lock`，等待 0 秒；外层/内部 exit code 均为 0；stderr 0 字节
- Build Summary: Total 1 / Success 1 / Failed 0
- 上游测试: 1341/1341；checks 716520/716520；test_package 3/3
- 原 Shadow CI test_package 3/3，L1e 破坏性反向验证通过
- AI 检视后真机最小复验（2026-08-16 01:40 +0800）：当前 `test.c` 重新编译运行，`liquid_nchoosek`、`liquid_version`、`windowf_index` 3/3 通过
- 门禁: L0 pass、L1 pass、L2 skip（库包无 bin）、L4 warn（补丁文本扫描，非阻塞）、L5 pass
- 安装产物：include/liquid/liquid.h、lib/libliquid.a、lib/cmake/liquid/、lib/pkgconfig/liquid-dsp.pc
- 上游 SHA256: abef8b2ddfd58c0a84ecda4f62158c4824b916144af4a2b07776e1a144d8cda4
- SHA512 与 vcpkg 官方记录一致: 83c55bf8...
- Path B 修复前：`liquid-staticConfig.cmake`/`liquid-staticTargets.cmake`，Config 引用不存在的 `liquidTargets.cmake`，canonical `find_package` 返回 1
- Path B 修复后：`liquidConfig.cmake`/`liquidTargets.cmake`，导出 `liquid::liquid-static`，最小消费者运行 PASS
- Path B runner：2026-08-15 22:50:09 至 22:50:52 +0800；全局 try-lock 等待 0 秒；exit 0

## 注意事项

- 静态库文件名为 `libliquid.a`，CMake 导出目标为 `liquid::liquid-static`，pkg-config 库名为 `liquid-dsp`。
- 安装时若用 DESTDIR 需先去掉 CMAKE_INSTALL_PREFIX 的绝对路径，否则 CMake 拼接路径失败。
- 上游 v1.8.0 起 CMake 为主构建系统，autotools 将逐步移除。

## Shadow CI 单包命令

```sh
CI_PACKAGES="archives/l/liquid-dsp/1.8.0.1" zsh ci/conan/build_and_test.sh
/path/to/run-ohos-shadow-ci.sh archives/l/liquid-dsp/1.8.0.1
```

验收需确认 `Build Summary` 的 `Total: 1`、L0/L1 pass，并看到 CTest
实际执行 `xautotest`（1341 项测试）及 test_package 消费者测试。

## 结束标记

最终状态: built
