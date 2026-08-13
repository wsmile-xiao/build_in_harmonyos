# megatools

## 简介

megatools 是一组用于从命令行访问 Mega.nz 云存储服务的程序。支持上传和下载单个
文件或整个目录树，支持流式下载（如预览视频和音频文件），也可通过 `megareg` 工具
注册新账户并完全控制加密密钥。

megatools 设计简洁高效，内存和 CPU 占用最低，速度尽可能快（受限于 Mega 服务器
限制）。代码干净易读，便于安全审计。

- **官方网站**: https://xff.cz/megatools/
- **License**: GPL-2.0-or-later (with openvpn-openssl-exception)
- **Homebrew formula**: https://github.com/Homebrew/homebrew-core/blob/master/Formula/m/megatools.rb

## 已编译版本

- **版本**: homebrew（对应上游 1.11.1.20230212）

## 编译方式（OHOS）

上游使用 Meson 构建系统，依赖 glib (gio-2.0)、openssl、libcurl。Homebrew formula
使用标准的 `meson setup build` + `meson compile` + `meson install` 流程。

OHOS 适配关键点：
1. **ar/ranlib 注入**: Conan MesonToolchain 只映射 c/cpp 编译器路径，不写入 ar/ranlib。
   meson 按裸名 `llvm-ar` 探测归档器，而 clang 工具链在 `/data/service/hnp/bin`（不在
   PATH 上），导致 configure 失败。从 c 编译器路径推导同目录的 `llvm-ar`/`llvm-ranlib`
   全路径，注入 `conan_meson_native.ini` 的 `[binaries]` 段。
2. **禁用 man 手册**: OHOS 无 asciidoc/db2x_xsltproc/db2x_manxml 工具链，设置
   `-Dman=false` 跳过手册页构建。
3. **glib-networking**: Homebrew formula 将其列为运行时依赖，但 megatools 使用 libcurl
   做网络通信，编译时不需要 glib-networking，省略此依赖。

```bash
# Conan 构建流程
conan create . --user=ohpcd --channel=stable \
  -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos \
  --build=missing
```

### OHOS 适配要点

- **Meson native file ar/ranlib 注入**: 从编译器路径推导 llvm-ar/llvm-ranlib 全路径
- **禁用 man 手册**: `-Dman=false`（OHOS 无 asciidoc 工具链）
- **依赖经 PkgConfigDeps 发现**: glib (gio-2.0)、openssl、libcurl 通过 .pc 文件发现

详见 `homebrew/notes.md`。

## 依赖

- glib 2.x（Worker 系统预编译包，提供 gio-2.0）
- openssl 3.5.6
- libcurl（Worker 系统预编译包）

## 安装产物

- `bin/megatools` — 主二进制（Mega.nz 云存储命令行客户端）

## 功能验证

```bash
megatools --version    # 查看版本信息
megatools --help       # 查看帮助信息
megatools ls --help    # 查看子命令帮助
```
