# sonivox 3.6.16 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，min 3.14；CMake 4.4.3 实测通过）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，target aarch64-linux-ohos）
- 设备: HarmonyOS PC（aarch64, HarmonyOS 6.1.0.117），profile `ohos-aarch64-device`
- 状态: built（conan-verify G0-G4 全 PASS，未 upload）

## 编译步骤

配方（`conanfile.py`）内全自动（CMakeToolchain + CMake，静态库默认，可选 CLI）：

```bash
# 1) 源码（官方 tag 归档；sha256 已在设备端复核）
#    https://github.com/pedrolcl/sonivox/archive/refs/tags/v3.6.16.tar.gz
#    sha256=8e9adf39a5e60c5b9ce4d1b79c83680cfab97d6e8eec6ffb6a3d0bad41413531
# 2) 配置（R32/本地 profile 提供 OHOS 三元组，无需手工 -DCMAKE_SYSTEM_NAME）
cmake -DBUILD_TESTING=OFF -DBUILD_EXAMPLE=ON -DBUILD_MANPAGE=OFF \
      -DBUILD_SONIVOX_STATIC=ON -DBUILD_SONIVOX_SHARED=OFF
# 3) 构建与安装
cmake --build . && cmake --install .
```

> 交付构建固定 `BUILD_TESTING=OFF`：开启测试时上游 configure 期会联网下载 81MB DLS
> 音色库并 FetchContent 拉取 GoogleTest，破坏 `conan create` 的自包含性。上游测试
> 在适配验证阶段以独立构建树原样运行（见下）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 提示 `System is unknown to cmake, create: Platform/HarmonyOS` | CMake 无 OHOS/HarmonyOS platform module（知识库 E092） | 仅提示信息，不影响构建：test_big_endian/find_library(m)/configure_file 均按通用 Unix 逻辑工作；实测 native 与 conan create 均零错误，配方不做平台宏或 -D 绕过 |
| 2 | 上游测试 configure 期需联网下载 81MB `Airfont_340.dls`（www.ronimusic.com）并校验 size=81362584 / MD5=40c0cd4ad29ae411a8fc3d6681002a2b | 上游 CI 设计 | 交付构建 `BUILD_TESTING=OFF`；验证阶段将 DLS 放在 `$TEMP/soundfont.dls`（校验通过后 configure 跳过下载），GTest 使用制品仓已有 `gtest/1.17.0`（本地缓存 OHOS 构建） |
| 3 | `sonivoxrender --version/--help` 退出码为 1 | 上游 `example/sonivoxrender.c` 的 `case 'v'/'h'` 分支 `return EXIT_FAILURE`（上游行为，非本适配引入） | 不修改上游行为；CI L2 smoke 对二者判 non-blocking warn（见 test-report.md「已知限制」） |

## 源码修改

**无补丁、零源码修改**：上游 v3.6.16 在 OHOS SDK clang 15.0.4 下原样编译通过
（静态库 + 共享库 + CLI + 上游测试全部构建成功）。`patches/` 目录不存在。

## 依赖版本

- 运行时依赖：无（仅 libm，OHOS sysroot 提供；pthread 由 libc 提供）
- 构建期依赖：无（交付构建不需要 GTest；验证阶段使用制品仓已有 gtest/1.17.0 缓存二进制）
- W0 预检（R35/R36）：`bash ci/scripts/preflight_check.sh sonivox/3.6.16` → 预检通过（无依赖需要检查）

## 上游测试清点与实测（R51）

| 项目 | 值 |
|------|----|
| 测试源 | `test/SonivoxTest.cpp`（GoogleTest 参数化套件，3 个 TEST_P） |
| 参数组 | 11 组（5 组无音色库 + 6 组加载 DLS），`gtest_discover_tests` 展开 |
| 用例总数 | **33**（3 × 11），ctest 注册 33 项 |
| 测试资源 | `test/res/{midi_a,midi8sec,midi_cs,midi_gs,ants}.mid` |
| 实测环境 | 真机 aarch64，OHOS clang 15.0.4，GTest 1.17.0（制品仓缓存），DLS 按上游 size+MD5 校验 |
| 实测结果 | **33/33 通过（100%）**，总耗时 20.41s |

## 验证结果

```bash
# 语言预检（R47）：C/C++（cmake 构建系统 + 源码统计），通过
python3 scripts/ohc-run.py lang-preflight sonivox 3.6.16 --src $BUILD_SRC_DIR
#   → 语言匹配: task=cpp, detected=cpp

# 配方本地验证（设备 profile，G0-G4）：
python3 scripts/ohc-run.py conan-verify sonivox 3.6.16 --profile ohos-aarch64-device
#   → Verdict: PASS（G0/G1/G2/G3/G4 全 PASS；conan create 成功，test_package 1/1 通过）

# 上游测试（独立构建树，上游源码原样）：
cmake -DBUILD_TESTING=ON -DCMAKE_PREFIX_PATH=<gtest-1.17.0> ... && cmake --build . && ctest
#   → 100% tests passed out of 33

# 消费者测试（conan create 阶段实跑，输出见 reports/conan-create.log 尾部）：
#   ./test_sonivox → 19/19 PASS（配置契约 5 + 渲染 11 + 负例 1 + 生命周期 2）

# 真机 CLI 功能验证（安装包内二进制）：
<package>/bin/sonivoxrender ants.mid > ants.pcm   # rc=0, 3816448 bytes（954112 帧 × 2ch × s16）
#   非静音校验：1838041/1908224 样本非零，峰值 32768
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libsonivox-static.a | 静态库（aarch64-linux-ohos，默认 `shared=False`） |
| include/sonivox/*.h | 公共头文件（eas.h 由 eas.cmake 模板生成） |
| bin/sonivoxrender | CLI：SMF MIDI → raw PCM（命令声明见软件级 commands.json，R38） |
| lib/cmake/sonivox/、lib/pkgconfig/sonivox-static.pc | CMake / pkg-config 元数据 |
| licenses/LICENSE | 上游 Apache-2.0 |
| share/man/man1/sonivoxrender.1 | 上游手册页 |

> 交付构建含可执行文件 → 软件级 `commands.json`（type=tool）已提供（R38/L0k）。

## 注意事项

- 版本号策略：首次适配使用上游版本 3.6.16（R37）。
- 无系统同名库冲突（G3 PASS）。
- 交付包为静态链接（`shared=False` 默认）；如需共享库可 `-o sonivox*:shared=True`。
- CI 验证：CI 对 GitHub 源自动加镜像 fallback（gh-proxy），本地验证期间以 `file://`
  指向同一 sha256 官方归档（与 CI 预下载机制等价），提交前已还原官方 URL。

## 对话记录

### 对话 #1 [2026-09-21]

- 问题: 设备无法直连 github.com 下载源码归档（curl 超时）
- 处理: 使用镜像（ghfast.top）获取同一 tar.gz，`sha256sum` 复核 == 官方
  8e9adf39…13531 后置入构建缓存；conan 侧验证同样以 sha256 等价的本地文件完成
- 结果: init-build / conan-verify / 上游测试全部基于官方等价源码完成

### 对话 #2 [2026-09-21]

- 问题: 上游测试需要 81MB DLS（站点对设备 IP 返回 403）
- 处理: 在 Windows 侧分块下载 Airfont_340.dls 并校验 MD5，经两跳 SSH 上传真机
- 结果: 上游 CMake 的 size+MD5 校验通过，33 个用例全部实跑

---

**编译结束**: 2026-09-21 17:56
**最终状态**: built
