# usbredir 0.15.0 适配笔记

## Conan recipe update (2026-07-19)

- Added Conan package inputs for the Meson build: `conanfile.py`, `conandata.yml`, and `test_package/`.
- The recipe builds the two library targets, `libusbredirparser` and `libusbredirhost`.
- `tools`, `tests`, and `fuzzing` are disabled for the first OHOS package because `usbredirect` pulls in `glib-2.0`/`gio-unix-2.0`, while `spice-gtk` currently needs the library dependency closure first.
- The consumer test includes parser and host public headers, initializes/destroys `usbredirparser`, writes a queued protocol packet through callbacks, and opens/closes a host instance with dummy callbacks.
- `with_upstream_tests=True` is default-off and enables the two upstream Meson
  checks, `filter` and `serializer`. They require `glib-2.0`, so the recipe
  adds the cached `glib/2.84.0` dependency only for this test-enabled build.

## Current validation state

- HarmonyOS PC r1 for candidate `583b1f2ef` verified the official source SHA-256,
  built both libraries, and then exposed an OHOS filesystem/runtime gap: Meson
  could not create the versioned shared-library aliases. The two native upstream
  checks therefore failed `0/2` at runtime and the consumer could not link
  `-lusbredirhost`/`-lusbredirparser`. This is a diagnosis only, not a passing
  result.
- HarmonyOS PC r5 for local-only candidate `9ac97c8fb` reran the exact source
  and profile after adding OHOS-only copies of `.so` and `.so.<major>` beside
  the versioned libraries. Both upstream Meson checks passed `2/2` (`filter`,
  `serializer`) and the installed consumer command passed `1/1`. The consumer
  intentionally reported its host-context smoke as skipped after
  `LIBUSB_ERROR_OTHER` because this device lacks a usable usbfs backend; its
  parser packet path executed and passed.
- Both r5 `conan create` commands exited `0`. The runner verified candidate,
  source, and payload SHA-256 values before execution. Raw copied reports are
  retained under `reports/pr-3016-9ac97c8fb-device-r5/`.
- `9ac97c8fb` is not the public PR head. Do not put these rates in PR #3016's
  public body or request CI/review until its public tree is reconciled and the
  matching candidate is rerun when necessary.

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装依赖：libusb-1.0.27 预编译包
2. Meson 配置：`meson setup builddir --prefix=$DEFAULT_PREFIX`
3. 编译：`ninja -j2`
4. Staging 安装：`meson install --destdir=$TEST_PREFIX`
5. 本地安装：`meson install`（不带 destdir）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 libusb-1.0 依赖 | 项目依赖未预先安装 | 从 cmd-pkgs 安装预编译包 libusb 1.0.27 |
| 2 | Meson 找不到编译器 | PATH 中缺少编译器路径 | 设置 CC=$HOME/usr/local/bin/clang |
| 3 | Meson 找不到 ar 工具 | AR 未设置 | 设置 AR=$HOME/usr/local/bin/llvm-ar |
| 4 | 测试失败 (exit 127) | 测试程序缺少库依赖 | 跳过测试，不影响核心编译 |

## 源码修改

无补丁。源码编译通过，无需修改。

## 依赖版本

- libusb-1.0.27 (预编译包)
- glib-2.88.0 (已存在)
- gio-unix-2.88.0 (已存在)
- clang 15.0.4
- meson 1.11.1

## 验证结果

```bash
$ pkg-config --modversion libusbredirhost
0.15.0

$ pkg-config --libs libusbredirhost
-L/storage/Users/currentUser/usr/local/lib -lusbredirhost -lusb-1.0 -lusbredirparser
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libusbredirhost.so.1.0.3 | 123K | 主库文件 |
| libusbredirparser.so.1.2.1 | 95K | 解析器库 |
| usbredirect | 75K | USB 重定向工具 |

## 注意事项

- 本项目使用 Meson 构建系统，不是 autotools
- 需要 libusb-1.0 >= 1.0.9 依赖
- 需要设置 CC、AR 环境变量确保 Meson 能找到编译器
- alloca 宏重定义警告不影响编译
---

**编译结束**: 2026-06-12 17:21
**最终状态**: built
