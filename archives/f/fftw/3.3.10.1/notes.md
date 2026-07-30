# fftw 3.3.10.1 适配笔记

`3.3.10.1` 是上游 FFTW 3.3.10 的 R37 适配修订版本；源码版本和源码 URL
保持 3.3.10，仅 Conan 包版本递增。

## 编译环境
- 构建系统: cmake（autotools 失败后改用）
- 编译日期: 2026-04-26
- 编译器: clang/clang++
- 状态: built（Conan CMake 配方和消费者测试通过）

## 编译步骤
1. 下载源码 `https://www.fftw.org/fftw-3.3.10.tar.gz`
2. 使用上游 CMake 构建，不修改或替换 `config.guess`/`config.sub`
3. CMake 配置: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..`
4. `make -j$(nproc)`
5. `make install`
6. 默认 `shared=False` 安装 `libfftw3.a`、头文件、pkg-config 文件和 CMake 配置文件；`shared=True` 时安装共享库

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Autotools configure 失败 | 旧 config.guess/config.sub 无法识别 OHOS | 当前配方改用上游 CMake 构建，不替换源码文件 |
| 2 | CMake policy 警告 | CMake 版本策略不兼容 | 设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | 官方 `bench -s 32x64` 长时间不结束 | OHOS 头文件定义 `CLOCK_SGI_CYCLE`，但运行时 `clock_gettime(CLOCK_SGI_CYCLE, ...)` 返回 `EINVAL`；FFTW 未检查返回值并反复重新计时 | 检查 SGI cycle clock 的运行时返回值，失败时回退到 `CLOCK_MONOTONIC`，保留默认 `FFTW_MEASURE` 语义 |
| 4 | shared 消费者的 `DT_NEEDED` 写入 Conan 缓存绝对路径 | OHOS 的 CMake 通用平台规则缺少 SONAME 参数；直接启用规则又会让上游 `VERSION/SOVERSION` 生成 HMDFS 不支持的版本软链 | 在 OHOS toolchain 补齐 SONAME/runtime linker flags，并让源码同时识别 CMake 的 `OHOS`/`HarmonyOS` 系统名后跳过 `VERSION/SOVERSION`，产出一个带 `SONAME=libfftw3.so` 的真实共享库 |

## 源码修改
当前配方应用 `patches/0001-use-monotonic-clock-on-ohos.patch`：在
运行时先尝试 `CLOCK_SGI_CYCLE`，调用失败时回退到 `CLOCK_MONOTONIC`；
支持 SGI cycle clock 的平台仍沿用原计时源。补丁同时在 OHOS/HarmonyOS
CMake 构建中跳过会生成版本软链的 `VERSION/SOVERSION` 属性。配方补齐 OHOS CMake 缺失的
SONAME/runtime linker flags。旧的 Autotools `config.guess`/`config.sub` 补丁仍保留在
基线版本 `../3.3.10/patches/` 中，作为历史诊断证据。

## 依赖版本
无外部依赖

## 注意事项
- 当前 OHOS 配方使用上游 CMake 构建。
- 需要设置 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
- 真机官方 CTest 入口保持为 `bench -s 32x64` 和 `bench -s ib256`，不得用
  `-oestimate` 改变测试语义。
- shared 消费者必须记录 `NEEDED libfftw3.so`，static 消费者不得包含该项；
  打包的共享库必须只有一个真实文件、无版本软链且 SONAME 与文件名一致。
