# carla 2.5.10 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

carla 是 Makefile 范式的 C++ 音频插件宿主项目，上游用 `make` 直接编译，无 configure 步骤。conanfile.py `build()` 中：
1. `apply_conandata_patches()` 应用两个适配补丁
2. `make -j1 CC=clang CXX=clang++` 编译完整 host（backend + bridges + plugin + frontend core）

`package()` 按 upstream `make install` 的布局复制产物：`bin/carla-single`（Python 启动脚本）→ `bin/`；`libcarla_*`、`carla-bridge-*`、`carla-discovery-*` → `lib/carla/`；`*.pc` → `lib/pkgconfig/`；头文件 → `include/carla/`；资源 → `share/carla/resources/`。并对 `carla-single` 和 `*.pc` 中的 `X-PREFIX-X` / `X-LIBDIR-X` / `X-INCLUDEDIR-X` / `VERSION` 占位符做替换。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `-fno-gnu-unique: unknown warning option`，clang 不识别 | `source/Makefile.mk` 在非 macOS/Windows/BSD 平台硬加 `-fno-gnu-unique`，这是 GCC 特有标志（控制 C++ weak symbol unique 化），clang 无此标志 | patches/0001：从 `source/Makefile.mk` 移除 `-fno-gnu-unique` |
| 2 | `'fts.h' file not found`，编译 ysfx 模块报错 | `source/modules/ysfx/sources/ysfx_utils_fts.cpp` 用 glibc 扩展 `<fts.h>` 的 `fts_open`/`fts_read`/`fts_close` 做目录遍历，鸿蒙 musl 不提供 `<fts.h>` | patches/0002：用 POSIX `nftw`（`<ftw.h>`，musl 有）重写 `visit_directories`，`thread_local` 全局承载 visitor 和 stop flag（nftw 回调无 user-data 参数） |
| 3 | `cc: No such file or directory`，make 找不到编译器 | `source/Makefile.deps.mk` 默认 `CC?=gcc` / `CXX?=g++`，鸿蒙工具链是 clang，无 gcc/g++ | conanfile.py `build()` 用 `make -j1 CC=clang CXX=clang++` 命令行参数覆盖（命令行参数优先级高于环境变量和 `?=` 赋值） |
| 4 | Conan `self.run(env=...)` 要求 list 非 dict | Conan 2.x 的 `run()` env 参数语义是 list of "KEY=VALUE" 字符串，且会替换而非追加环境 | 早期尝试用 dict 报 AssertionError；改用 make 命令行参数传 CC/CXX，绕开 env 注入问题 |
| 5 | `carla-discovery-native --version` 退出 1 | 上游 CLI 无 `--version` 标志，`--version` 被当未知 `<type>` 参数，打印 usage 后退出 1 | test_package 改用无参数调用，断言 stdout 含 `usage:`（二进制存活的真实信号），不依赖 returncode（退出码在不同构建间不稳定，0 或 1） |
| 6 | 本地 `conan create` 卡在下载源码（github.com 不可达） | 本地网络无法访问 github.com，conan `get()` 下载超时 | conanfile.py `source()` 加本地 fallback：读 `CARLA_LOCAL_TARBALL` 环境变量指向的 tarball；**显式调用 `check_sha256(self, local_tar, src_meta["sha256"])` 后再 `unzip()`**，sha256 取自 conandata.yml，与在线 `get()` 走同一条校验路径 |

## 源码修改

- patches/0001-drop-fno-gnu-unique-for-clang.patch：移除 `source/Makefile.mk` 的 `-fno-gnu-unique` 标志
- patches/0002-replace-fts-with-nftw-for-musl.patch：重写 `source/modules/ysfx/sources/ysfx_utils_fts.cpp`，用 POSIX `nftw` 替代 glibc `fts`

## 依赖版本

- 无任何必需运行时依赖。carla 是 application 类型（`cpp_info.libdirs = []`），所有音频驱动（ALSA/JACK/PulseAudio）、GUI（Qt）、插件格式（LV2/VST）都是可选功能，pkg-config 检测不到就跳过

## 验证结果

```
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
→ 构建通过（16 个静态库、桥接 .so、discovery 二进制全部生成）
→ test_package 通过（carla-discovery-native 存活验证 + libcarla_utils.so 存在）
→ carla/2.5.10 (test package): Conan test_package: carla binaries verified OK
```

## 注意事项

- carla 的 Makefile 假定 GCC 工具链（`CC?=gcc`），鸿蒙 clang 环境必须用 make 命令行参数显式传 `CC=clang CXX=clang++`
- `carla-discovery-native` 无 `--version` 标志，存活验证应用无参数调用看 usage 输出
- 本地离线验证可用 `CARLA_LOCAL_TARBALL` 环境变量指向预下载的 tarball 绕过网络

---

**编译结束**: 2026-07-28
**最终状态**: built
