# plutovg 1.3.3 适配笔记

## 编译环境

- 目标 worktree：`feat/plutovg-1.3.3`
- 构建系统：CMake
- 编译日期：2026-08-28
- 目标平台：HarmonyOS PC arm64（OHOS/aarch64）
- 编译器：`/data/service/hnp/bin/clang` 15.0.4
- Conan：2.29.1（OHOS 适配版）
- Conan profile：`ci/conan/profiles/ohos-aarch64`
- 状态：built（已通过本地 Conan/W3，尚未上传制品仓）

## 编译步骤

1. W0 预检：`preflight_check.sh plutovg/1.3.3`，确认无 Conan 依赖；仓库中没有 plutovg 历史归档。
2. 从官方仓库下载 `v1.3.3` 源码，SHA256 为 `2b0d17a6e016f47b86f9c00e2cb82600041b1ea1f7d2a00c2d46ae542cbfed3c`。
3. 探索构建：`cmake -S . -B build -DCMAKE_BUILD_TYPE=Release`，随后 `cmake --build build --parallel 1`，成功生成静态库和上游 `smiley` 示例。
4. 运行 `build/examples/smiley`，成功生成 150x150 PNG 图像。
5. 通过 `ohc-run.py conan-init plutovg 1.3.3 --force` 生成配方；配方默认 `shared=False`，同时构建并运行上游 `smiley` 示例。
6. 通过 Conan 创建和消费者测试：`conan-verify`、W3 `build_and_test.sh` 均通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 将工程识别为 autotools | 上游同时提供 CMake/Meson 文件，但初始化检测选择了错误的构建类型 | 根据实际 `CMakeLists.txt` 将版本 manifest 的构建系统修正为 CMake，再运行 `conan-init` |
| 2 | 第一次 `conan-verify` 报 `settings.os.version` 未定义 | 传入相对 profile 路径时 Conan 将其当作 profile 名称并自动生成了错误 profile | 使用目标仓库 `ci/conan/profiles/ohos-aarch64` 的绝对路径；实际 profile 为 `os=OHOS`、`os.version=6.0`、`libc++` |
| 3 | 消费者测试找不到 `plutovg.h` | CMake install 将公共头安装到 `include/plutovg/`，而 Conan 默认只暴露 `include/` | 在 `package_info()` 中声明 `includedirs = ["include/plutovg", "include"]`，兼容上游两种 include 写法 |
| 4 | `finish` 的 G0 clean verifier 报 configure exit 127 | 仓库旧版 `clean_verify` 固定执行 Autotools `configure`，不识别 CMake-only 源码 | 保留原始日志；以 Conan G2 和 W3 的实际 CMake 构建作为当前 Conan 体系验证依据，未修改框架脚本 |

## 源码修改

无。上游源码不需要 OHOS 补丁，`patches/` 不创建。

## 依赖版本

- Conan 依赖：无。
- 系统依赖：C 标准库、libm、pthread，由上游 CMake 自动探测，并在 `package_info()` 中声明系统库。

## 验证结果

```text
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 1                         # PASS
build/examples/smiley                                    # PASS，生成 PNG
python3 scripts/ohc-run.py conan-verify plutovg 1.3.3 \
  --profile=/storage/Users/currentUser/ws/plutovg-1.3.3/ci/conan/profiles/ohos-aarch64 \
  --user=ohpcd --channel=stable                           # PASS
python3 scripts/ohc-run.py finish plutovg 1.3.3 built      # W3 PASS；旧 G0/摘要步骤有框架兼容性警告
```

- Conan G1/G2/G3/G4：PASS。
- Conan test_package：1/1 通过，真实调用版本、矩阵、光栅化和 PNG API。
- W3 本地 CI：1/1 包通过，L0/L1/L1e/L4/L5 通过，100%。
- W3 中的 CMake 配置产生 CMake 对 HarmonyOS 平台模块未知的提示，但编译、链接、示例运行和消费者测试均成功。

## 发现与知识

- ✅ `CMakeLists.txt` 和 `meson.build` 同时存在时，Conan 配方应明确选择并验证实际构建入口。
- ✅ 安装到 `include/plutovg` 的单头文件库需要在 `package_info()` 中显式暴露嵌套 include 目录。
- ✅ 无 Conan 三方依赖的静态库仍应声明其 `libm`/`pthread` 系统链接依赖。
- ✅ Conan OHOS toolchain 下的 CMake unknown-platform 提示对应 E267；本库无平台分支需求，保持上游源码不打补丁。

## 已知限制

- 上游没有独立的 CTest/单元测试套件；官方工作流只构建 Meson/CMake 工程。本适配将上游 `examples/smiley.c` 构建并运行作为上游功能检查，并额外提供 Conan 消费者测试。
- `finish` 的旧版 G0/submit readiness 仍包含 Autotools 和废弃 `packaging/` 假设；当前 Conan 归档按 `knowledge/ARCHIVE-SPEC.md` 使用 Conan 制品，不生成手工 tar.gz。
---

**编译结束**: 2026-08-28 23:50
**最终状态**: built
