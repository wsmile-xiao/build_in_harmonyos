# precomp - 压缩再压缩（预压缩）命令行工具

## 简介

precomp（precomp-cpp）是 Christian Schneider 开发的命令行预压缩器。
它扫描文件中已被压缩的流——deflate/zlib/gzip、bZip2、GIF、JPG、MP3、
ZIP、PDF、SWF、MIME Base64、LZMA——尝试将内层数据解压出来，并在能
"重新压缩到与原流位对位一致"的前提下，把解出的数据连同重建信息写入
.pcf（PreCompressedFile）容器。.pcf 本身可能比原文件大，但用比 deflate
更强的压缩器（xz/7z 等）再压 .pcf 时，总压缩比显著优于直接压原文件；
用 `precomp -r` 可从 .pcf 无损还原原文件（字节级一致）。自 0.4.3 起
Linux 与 Windows 版本产生的 PCF 文件互相兼容。

典型用法：

```bash
precomp archive.zip                 # 生成 archive.pcf（默认 LZMA2 容器）
xz -9 archive.pcf                   # 强压缩器再压，优于直接 xz 原文件
precomp -r archive.pcf              # 无损还原 archive.zip
```

## 功能特点

- 流类型检测：PDF/ZIP/GZip/PNG/GIF/JPG/SWF/MIME Base64/bZip2/MP3，可
  用 `-t[+-][pzgnfjsmb3]` 开关增删
- 递归解嵌套流（ZIP 内 ZIP 等），`-d[depth]` 控制深度（默认 10）
- 容器压缩方式：`-cl`（LZMA2，默认）/`-cb`（bZip2）/`-cn`（不压缩，
  交给外部压缩器）
- `-v` 详细调试模式、`-longhelp` 完整开关说明
- 适配新增 GNU 风格 `--version`/`--help`（打印横幅/用法后 exit 0，
  便于脚本与包管理器探测）

## 上游与构建

- 上游仓库：https://github.com/schnaader/precomp-cpp （tag v0.4.7）
- 许可证：Apache-2.0（README Credits 节另列 vendored 组件版权）
- 构建系统：CMake（C++11），产物为单二进制 `precomp`
- 依赖：零 conan 依赖——bzip2/zlib/giflib/liblzma/packJPG/packMP3/
  preflate 全部 vendored 于 contrib/ 并编进二进制；唯一外部依赖
  pthreads（musl libc 自带）

## 鸿蒙 PC（OHOS aarch64）适配要点

- CMake 对 HarmonyOS 系统名不设置 UNIX 变量，上游 `if (UNIX)` 平台
  分支不生效：配方以 `CMAKE_SYSTEM_NAME=Linux` 原生配置（musl +
  libc++，无 Linux 专有 API），UNIX 分支（-DUNIX、Threads）正常工作
- 上游 `cmake_minimum_required(VERSION 3.2)` 与 CMake 4.x 不兼容：
  注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
- 上游 CMakeLists 无 install() 规则：package() 手动布局 `bin/precomp`
- 补丁（patches/0001）：precomp.cpp 新增 `--version`/`--help` 长选项
  处理（exit 0），不改既有行为
