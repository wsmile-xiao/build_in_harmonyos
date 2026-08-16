# gnome-autoar 0.4.5 HarmonyOS 前置适配记录

## 当前状态

- issue: 2147
- 分支: `feat/gnome-autoar-0.4.5-2147`
- 阶段: W0、源码分析、Conan 配方、`test_package`、真机 shadow CI 和生产 CI 已完成
- 状态: PR #5323 评审修订中；生产 CI #26007 已通过

## W0 依赖检查

2026-08-14 使用 Conan 2.29.1、独立 `CONAN_HOME` 和 `ohpcd` remote 执行
`conan download <ref> -r=ohpcd --only-recipe`。以下配方均存在：

- `glib/2.84.0.1`
- `libarchive/3.8.7`
- `libffi/3.4.4`
- `pcre2/10.45`
- `zlib/1.3.1.1`
- `xz/5.6.2`

因此本库没有缺失硬依赖，不需要把依赖适配混入 issue 2147。

真机上的 `libarchive/3.8.7` 不含 crypto backend；这不是 gnome-autoar 的硬构建依赖
缺失。若后续要求验证加密 ZIP 解密，应单独适配 libarchive 的 crypto 能力。

## 源码与构建系统

- 官方源码：`https://download.gnome.org/sources/gnome-autoar/0.4/gnome-autoar-0.4.5.tar.xz`
- 官方和本机实算 SHA256：`838c5306fc38bfaa2f23abe24262f4bf15771e3303fb5dcb74f5b9c7a615dabe`
- 构建系统：Meson（最低版本 0.56.0）
- 硬依赖：`glib-2.0`、`gio-2.0`、`gobject-2.0` >= 2.35.6，
  `libarchive` >= 3.4.0
- 关闭的可选功能：GTK 3、GObject Introspection、Vala、GTK Doc
- 保留功能：核心 archive API 和上游测试

官方 tarball 含一个用于路径安全测试的绝对 `/tmp` 符号链接。Windows 原生 tar
不能创建该链接，所以本机分析解包会报告这一项失败；配方在 Windows 源码检查时排除
该单个夹具，在类 Unix/OHOS 环境对校验通过的官方 tarball 使用 trusted filter 保留它。

## 配方策略

1. `PkgConfigDeps` 向 Meson 提供 GLib 和 libarchive 元数据。
2. 在生成阶段补齐 GLib `.pc` 的 `glib_mkenums` 变量，并从 Conan
   `compiler_executables` 注入 `ar`、`ranlib`，不依赖交互式 shell 环境。
3. 使用 `TMPDIR` 指向 build 目录下的可写路径。
4. 补丁将上游 `shared_library()` 改为 `library()`，默认构建静态库，避免首次
   真机验证受 HarmonyOS 动态加载命名空间影响，同时仍保留 `shared=True` 选项。

OHOS runner 的 pkgconf 旁存在过期 `libpkgconf.so.7`，配方在 build 目录内复制匹配的
`libpkgconf.so.7.0.0` 并通过 `/bin/sh` wrapper 调用，不修改设备全局安装。缓存中的
Python 构建工具同样通过解释器显式调用。`test_package` 使用 Meson，并注入 SDK 同目录
的 `llvm-ar`、`llvm-ranlib`，不依赖真机缺失的 CMake。

## 测试说明

上游 `tests/meson.build` 构建 3 个非 GTK 测试工具，并注册
`test-extract-unit` 到 Meson。该二进制包含 22 个 GLib 测试项，覆盖普通/加密归档、
冲突处理、软硬链接、路径净化和只读目录。配方启用 `tests=true` 并在非交叉构建时
执行 `meson.test()`；不吞掉失败。

`test_package/test.c` 实质调用格式 API 和 `AutoarCompressor`，创建 ZIP 文件，检查
`completed` 信号、目标文件类型和非零大小，不是打印字符串的空壳测试。

两个符号链接用例先运行符号链接能力探针；仅在返回“不支持”或“权限拒绝”时标记 skip。
设备沙箱的独立 `ln -s` 诊断也返回 `Permission denied`，且上游会在函数返回前因重复设置
`GError` 触发 SIGTRAP。两个
加密解密用例先执行，仅当 libarchive 返回 `Decryption is unsupported` 时动态 skip；
其余 18 个用例保留原始断言并通过。

## 已完成的本机验证

- W0 直接及传递依赖 recipe 下载：通过
- GNOME 官方 checksum 与本机 SHA256：一致
- Meson 构建选项和 22 个上游测试注册项：已核对
- Python 语法、YAML、patch dry-run、Conan recipe source/inspect：见质量报告
- HarmonyOS 构建、上游测试和消费者测试：review rerun 通过

## 真机 shadow CI 结果

- endpoint: `currentUser@10.62.218.131:2222`
- runner: `codex-0.4.5-gnome-autoar-0.4.5-2147-shadow-20260814-r1-conan-20260814-182832-24551`
- exit code: `0`
- upstream: 22 total，18 passed，0 failed，4 skipped
- consumer: `gnome-autoar 0.4.5 consumer test: OK`
- L0: pass
- L1: pass（upstream tests + test_package executed）
- L2: skip（库包无 `bin/`，符合预期）
- L4: pass（patches clean）
- L5: pass（`lib/` 有产物）
- Build Summary: Total 1，Success 1，Failed 0
- 最新基础设施复验 runner:
  `codex-gnome-autoar-gnome-autoar-0.4.5-2147-infra-path-r22-20260816-122207-5462`
- 生产 CI: #26007，通过

## 路径 B 知识草稿

已新增仅与 gnome-autoar/2147 直接相关的草稿：

- `knowledge/drafts/DRAFT-gnome-autoar-runtime-capability-skip-2147.kv`
- `knowledge/drafts/DRAFT-gnome-autoar-runtime-capability-skip-2147.md`

草稿沉淀“先执行目标能力，再仅对精确能力错误最小化 skip”的上游测试移植模式，覆盖
符号链接沙箱能力、依赖 crypto backend、同步/异步完成时序和 pass/skip 分层统计；不修改
正式知识图谱、索引或基础设施。

## 下一步命令

```sh
# 真机或项目 shadow CI runner 中，只跑本包
CI_PACKAGES="archives/g/gnome-autoar/0.4.5" zsh ci/conan/build_and_test.sh

# 使用 shadow CI 包装器时
/path/to/run-ohos-shadow-ci.sh archives/g/gnome-autoar/0.4.5
```

后续 shadow CI 复验应继续确认 `Total: 1`、L0/L1/L4/L5 通过，并审阅 L2 的
library-only skip 以及 4 个能力相关的上游测试 skip。
