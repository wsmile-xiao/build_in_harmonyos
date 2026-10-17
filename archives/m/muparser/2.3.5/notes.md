# muparser 2.3.5 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang/clang++ (15.0.4, aarch64-unknown-linux-ohos, OHOS SDK 26.0.0.18)
- 状态: published
- 主机: HarmonyOS (HongMeng Kernel 1.12.0), aarch64

## 编译步骤

```bash
# 官方源码 v2.3.5（GitHub archive），SHA-256 与 conan-center 官方记录一致
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTING=ON -DENABLE_SAMPLES=OFF -DENABLE_OPENMP=OFF \
  -DCMAKE_INSTALL_PREFIX=<prefix>
cmake --build build -j$(nproc)
# 上游测试
LD_LIBRARY_PATH=build ./build/t_ParserTest   # 604 expressions, 全部通过
# 鸿蒙专项测试
./t_ohos_muparser_test                        # 8 项全部通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时（source 下载） | 网络到 github.com:443 不可达 | codeload.github.com 直连成功，SHA-256 与官方一致；conandata.yml 双 URL 兜底 |
| 2 | conan-init 生成 Autotools 模板 | 模板按 registry 缺省生成 | 按 templates/conanfile-cmake.py.tmpl 重写为 CMake 配方 |
| 3 | ENABLE_OPENMP=ON 需 find_package(OpenMP REQUIRED) | 上游默认开启，CI 无 OpenMP | 配方 generate() 设 ENABLE_OPENMP=OFF |
| 4 | W3 junk_check 全仓扫描误命中其他库基线遗留文件（flatcv/goaccess 等） | 本分支尚无提交，diff 为空回退 full 模式 | 提交仅含 muparser 的原子 commit 后，W3 进入 incremental 模式只扫本 PR 文件 |

## 源码修改

无补丁（上游 CMake 项目直接构建通过）。

## 依赖版本

无第三方依赖（纯 C++ 数学解析库，零依赖）。

## 验证结果

- 上游单元测试: `t_ParserTest` → Test passed (604 expressions), exit 0
- 鸿蒙专项测试: `t_ohos_muparser_test` → 8/8 通过 (uname 确认 HarmonyOS / HongMeng Kernel 1.12.0 / aarch64)
- conan-verify: G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS
- 消费者验证: consumer_demo `(1+2)*3^2 = 27.0` 运行成功

## 注意事项

- 版本号 2.3.5 为首次适配，无后缀（R37）
- 库类型（.a/.so），无可执行产物，不需要 commands.json（R38）
---

**编译结束**: 2026-09-02 03:23
**最终状态**: published
