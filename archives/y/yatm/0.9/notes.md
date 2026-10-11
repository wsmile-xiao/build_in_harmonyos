# yatm 0.9 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-09-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 官方源码：`https://github.com/mlang/yatm/archive/refs/tags/v0.9.tar.gz`
2. SHA256：`87ac061b7169669d7acab2daa5cf1674c9a355653118a5ccc259362ac4505248`
3. 使用 Conan `PkgConfigDeps` 生成 `ao/libmad/ogg/slang/sndfile/soundtouch/speex` 的 pkg-config 文件。
4. 使用 `CMakeToolchain` 配置并构建上游 `yatm` 可执行文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMake 使用 `pkg_search_module(MAD REQUIRED mad)` | Conan `libmad/0.15.1b` 的 PkgConfigDeps 文件名为 `libmad.pc` | 将上游 CMake 的模块名改为 `libmad`，其余探测逻辑不变 |
| 2 | `slang/2.3.3` 的头文件使用 C++17 已移除的 `register` 参数修饰 | Conan profile 使用 C++17 | 在 CMakeToolchain 中追加 `-Wno-register`，保持上游源码不改 |
| 3 | CI #65779 并行 make 失败 | HMDFS 不支持 GNU make jobserver FIFO | CMake build 显式 `-j1` |
| 4 | CI #65806 运行 `yatm` 失败，缺 `libpulse*` 与 `sf_*` | `libpulsecommon-17.0.so` 先于 `libsndfile.a` 提供 `sf_*`，未签名的 PulseAudio 共享库进入 NEEDED | `target_link_libraries` 将 `SNDFILE` 提前，并追加 `-Wl,--as-needed`；`sndfile` 静态解析，NEEDED 不再包含 pulse |
| 5 | CI #65888 运行 `yatm` 报 `Unknown terminal: dumb` | Slang 初始化需要 terminfo 数据库中存在的 TERM | 测试改用 `TERM=xterm` |

本次将问题 4 沉淀为 `knowledge/drafts/DRAFT-yatm-0.9-shared-symbol-export-link-order.kv/.md`，主题为“传递共享库导出同名符号导致链接顺序抢占与未签名 NEEDED 依赖”。

## 源码修改

- `patches/0001-CMakeLists.txt.patch`：将 CMake 最低版本从 2.8 提升到 3.5，适配 CMake 4；将 MAD pkg-config 模块名改为 Conan 生成的 libmad；并将各依赖的 Conan 库目录传给链接器。

## 依赖版本

依赖均已在 `ohpcd` 制品仓用 `conan download ... --only-recipe` 验证：

- libao-pulse/1.2.2
- libmad/0.15.1b
- libsndfile/1.2.2
- soundtouch/2.0.0
- slang/2.3.3
- speex/1.2.1
- libogg/1.3.6

## 上游测试清点

源码包仅有 `CMakeLists.txt`、`COPYING`、`ChangeLog`、`README`、`config.h.in`、`yatm.1`、`yatm.cc`。
全包文件名与内容扫描未发现 tests/check/spec/regression/fixture、`add_test`/CTest、断言或 corpus。
计数口径：正式测试 case 数。上游测试数：0。

## 验证结果

```bash
已通过：`python3 scripts/ohc-run.py conan-verify yatm 0.9 --profile ohos-local`（本地交叉构建）

远程 HarmonyOS CI：通过（build #66596），4/4 个消费者检查项通过。

鸿蒙特有消费者测试：在 `HOME/.libao` 写入 `default_driver=null`，生成 0.1 秒静音 WAV，实际执行 `yatm -q -e 0.1 test.wav`。测试断言共 4 项：安装产物可执行、null 驱动配置存在、WAV 样本非空、真实播放路径退出码为 0。
```

## 交付物

- Conan package: `yatm/0.9`
- Executable: `bin/yatm`
- Manual page: `share/man/man1/yatm.1`

## 注意事项

- 本机为交叉构建，`test_package` 因 `can_run=False` 跳过；真实运行留给远程 HarmonyOS worker。
---

**编译结束**: 2026-09-30 20:53
**最终状态**: built
