# arturo 0.10.0 适配笔记

## 编译环境
- 构建系统: custom (Nim build.nims)
- 编译日期: 2026-08-18
- 编译器: clang/clang++
- 状态: built

## 编译步骤

Arturo 使用 Nim 构建系统（build.nims），不是传统的 CMake/Autotools/Meson。
编译过程如下：

1. **源码获取**：从 GitHub 下载 v0.10.0 tag 的 tarball，自动解压。
2. **补丁应用**：通过 `apply_conandata_patches(self)` 应用 6 个补丁。
3. **依赖准备**：从 Conan 依赖（self.dependencies）收集 include 和 lib 文件到
   build 文件夹的 deps_prefix/ 目录。替换源码中内嵌的 OpenSSL 和 PCRE 静态库
   为 OHOS 兼容版本。
4. **环境设置**：通过 `conan.tools.env.Environment` 设置环境变量
   NIM_LIB_PATH、DEPS_INCLUDE_DIR、DEPS_LIB_DIR，供补丁中修改的 build.nims
   和 config.nims 通过 `os.getEnv()` 读取。
5. **编译命令**：
   ```bash
   nim build.nims build --mode:full --os:linux --arch:arm64 --log
   ```
   `--mode:full` 启用完整构建模式（GMP、OpenSSL、SQLite、PCRE 支持）。
   `--os:linux --arch:arm64` 指定目标平台。
6. **签名**：使用 `binary-sign-tool` 对产出的 ELF 二进制进行自签名
   （HarmonyOS 要求）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | WebKit2GTK (webview) 不可用 | HarmonyOS 无 WebKit2GTK/GTK 库 | 在 buildmode.nims 中添加 `--define:NOWEBVIEW` 禁用 webview 模块 |
| 2 | X11 clipboard 不可用 | HarmonyOS 无 X11 库 | 在 buildmode.nims 中添加 `--define:NOCLIPBOARD` 禁用 clipboard 模块 |
| 3 | httpClient 模块名大小写错误 | Nim 2.x 对模块名大小写敏感，源码中使用 `httpClient` 而非 `httpclient` | 修改 datasource.nim、packager.nim、vquantity.nim 中的 import 语句 |
| 4 | Nim stdlib 路径未找到 | build.nims 构建的 nim compile 命令需要显式指定 stdlib 路径 | 在 build.nims 的 compile() 函数中添加 `--lib` 和 `--path` 标志，通过 `os.getEnv("NIM_LIB_PATH")` 动态获取路径 |
| 5 | 依赖头文件和库未找到 | Conan 管理的依赖不在系统标准路径 | 在 config.nims 中通过 `switch("passC", ...)` 和 `switch("passL", ...)` 添加依赖路径，通过 `os.getEnv()` 动态获取 |
| 6 | 内嵌 OpenSSL/PCRE 与 OHOS 不兼容 | 源码 src/deps/ 中内嵌的预编译库基于 glibc，OHOS 使用 musl | 用 Conan 管理的 OpenSSL/PCRE 静态库替换 src/deps/ 中的内嵌版本 |
| 7 | configWebkit 在非 webview 模式下仍执行 | 原始代码在 linux/freebsd 平台无条件调用 configWebkit() | 用 `not defined(NOWEBVIEW)` 守卫条件，避免在禁用 webview 时执行 |

## 源码修改

共 6 个补丁，通过 `apply_conandata_patches(self)` 自动应用：

| 补丁文件 | 修改内容 |
|----------|----------|
| 0001-.config-buildmode.nims.patch | 在 fullBuildConfig() 中添加 `--define:NOWEBVIEW` 和 `--define:NOCLIPBOARD`，禁用 WebKit2GTK 和 X11 clipboard |
| 0002-build.nims.patch | 在 compile() 函数中添加 Nim stdlib 路径（通过 `os.getEnv("NIM_LIB_PATH")` 动态获取）和 `--cc:clang` 标志 |
| 0003-config.nims.patch | 添加 `--cc:clang` 和 stdlib 路径（通过 env var）；添加依赖 include/lib 路径（通过 env var）；用 `not defined(NOWEBVIEW)` 守卫 configWebkit() |
| 0004-src-helpers-datasource.nim.patch | 修复 `import httpClient` → `import httpclient`（Nim 2.x 大小写敏感） |
| 0005-src-vm-packager.nim.patch | 修复 `import httpClient` → `import httpclient` |
| 0006-src-vm-values-custom-vquantity.nim.patch | 修复 `import httpClient` → `import httpclient` |

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| gmp | 6.3.0 | 大数运算支持 |
| mpfr | 4.2.2 | 多精度浮点运算 |
| openssl | 3.5.6.1.1 | SSL/TLS 加密支持 |
| sqlite3 | 3.49.1 | SQLite 数据库支持 |
| pcre | 8.45 | 正则表达式支持 |

所有依赖均已发布到 ohpcd 制品仓（W0 通过）。

## 验证结果

```bash
# conan create 验证（使用 ohos-aarch64 profile）
conan create archives/a/arturo/0.10.0/conanfile.py \
  --build=missing \
  -pr:b ci/conan/profiles/ohos-aarch64 \
  -pr:h ci/conan/profiles/ohos-aarch64

# 产物：bin/arturo 可执行文件
# test_package：执行 arturo --version 验证版本输出
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（R33 合规，无硬编码路径） |
| conandata.yml | 源码 URL（R39 合规，官方 GitHub）+ 6 个补丁声明 |
| patches/0001-0006 | 6 个补丁文件 |
| test_package/ | Conan L1 测试（R34 合规，执行 arturo 二进制） |
| manifest.yaml | 编译元数据 |
| commands.json | 命令行工具声明（R38 合规，binary: true） |

## 注意事项

- Nim 构建系统不使用 CMake/Autotools，conanfile.py 的 `build()` 方法直接调用
  `nim build.nims build` 命令。
- 环境变量 NIM_LIB_PATH、DEPS_INCLUDE_DIR、DEPS_LIB_DIR 由 conanfile.py 的
  `generate()` 方法通过 `conan.tools.env.Environment` 设置，供补丁中修改的
  Nim 源文件通过 `os.getEnv()` 读取。
- WebKit2GTK (webview) 和 X11 (clipboard) 在 HarmonyOS 上不可用，通过
  NOWEBVIEW 和 NOCLIPBOARD 编译定义禁用。
- 内嵌的 OpenSSL 和 PCRE 静态库必须替换为 Conan 管理的 OHOS 兼容版本。
---

**编译结束**: 2026-08-19 11:34
**最终状态**: built
