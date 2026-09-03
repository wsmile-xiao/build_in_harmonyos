# tinygltfloader 0.9.2 适配笔记

## 编译环境
- 构建系统: Makefile（header-only C++ 库）
- 编译日期: 2026-09-03
- 编译器: clang/clang++（Conan 配方从 `tools.build:compiler_executables:cpp` 获取）
- 状态: built（待设备与 CI 闭环）

## 编译步骤

1. 从 `v0.9.2` 官方 tarball 解压源码，SHA256 为
   `423b487c36f128eb4c950906566da5fad24e3d5f4a9a99b1f20f78ac31c3a947`。
2. 原始 `make -j1` 使用 `g++ -Wall -Werror -g -O2`，在 Clang 下因两处布尔表达式位运算告警失败。
3. 将 `tiny_gltf_loader.h` 中 `v.contains(...) & v.get(...).is<std::string>()` 的两处 `&` 改为逻辑运算 `&&`，通过 `refresh-patch --auto` 生成 `0001-tiny_gltf_loader.h.patch`。
4. 配方构建阶段使用 Conan host profile 的 `clang++`，以相同的 `-Wall -Werror -g -O2` 编译并运行官方 `loader_test box.gltf`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 `make -j1` 失败 | Clang 将布尔表达式的位运算 `&` 报为 `-Wbitwise-instead-of-logical`，上游 `-Werror` 将告警升级为错误 | 以逻辑语义修正为 `&&`，生成并应用 `0001-tiny_gltf_loader.h.patch` |
| 2 | `make check` 无法执行 | 上游 Makefile 只定义 `all`，没有 `check` 目标 | 记录为上游测试入口缺失；执行官方 `make` 目标及 `loader_test box.gltf` |
| 3 | `test_runner.py` 未执行 | 上游要求 Python 2.6/2.7 和外部 glTF Sample Models，当前环境无 `python2`，脚本也含 Python 2 `print` 语法 | 记录为有证据的环境/测试入口限制，不将其计作失败；用仓库自带 `box.gltf` 完成官方 loader smoke test |

## 源码修改

- `patches/0001-tiny_gltf_loader.h.patch`：修复两处布尔条件的 `&` → `&&`，保持语义不变并兼容 Clang `-Werror`。

## 依赖版本

- Conan 依赖：无；picojson 与 stb_image 随上游源码作为头文件一同打包。

## 验证结果

```bash
make -j1                         # patched upstream target: PASS
./loader_test box.gltf           # official fixture smoke test: PASS
clang++ -std=c++17 -Wall -Werror test_package/test.cpp -I <package-include>
./test_tinygltfloader            # consumer checks: 6/6 PASS (local static check)
```

## HarmonyOS 设备验证

- 远端 worktree: `$HOME/ws/wt-tinygltfloader-0.9.2`，分支
  `feat/tinygltfloader-0.9.2`，提交 `711ffbc1b217793bf86a46edcb54bfb24affee6d`。
- 使用 `ci/conan/profiles/ohos-aarch64` 在 HarmonyOS HongMeng Kernel 1.12.0
  aarch64、Conan 2.29.1、Clang 15.0.4 上执行：
  `conan create archives/t/tinygltfloader/0.9.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`。
- 首次配方尝试因错误读取 `tools.build:compiler_executables:cpp` 失败；按实际
  profile 字典结构修复后重新执行，`conan create` 通过，官方 `loader_test`
  通过，包安装 3 个头文件，`test_package` 输出
  `tinygltfloader consumer test: 6 checks passed`。
- 随后执行 `python3 scripts/ohc-run.py conan-verify tinygltfloader 0.9.2
  --profile ohos-aarch64 --user ohpcd --channel stable --project-dir "$PWD"`，
  G1/G2/G3/G4/L2/L4/L5 全部通过；报告保存在远端 worktree 的
  `archives/t/tinygltfloader/0.9.2/reports/conan-verify-report.md`。
- 远端 worktree 仅保留既有且与本包无关的 `archives/l/libXext/README.md`、
  `archives/l/libXext/manifest.yaml` 大小写冲突改动；tinygltfloader 及其构建
  输入在目标提交上无未提交改动。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/tiny_gltf_loader.h` | 主 API 头文件 |
| `include/picojson.h` | 上游自带 JSON 依赖头文件 |
| `include/stb_image.h` | 上游自带图像解码依赖头文件 |

## 注意事项

- 上游项目已将 TinyGLTFLoader 标记为 deprecated，面向 glTF 2.0 的项目应评估后续 `tinygltf`。
- 该包不生成 `.a`/`.so` 或命令行工具，因此不创建软件级 `commands.json`；Conan `package_info()` 暴露 header-only CMake target `tinygltfloader::tinygltfloader`。
