# mklittlefs

> LittleFS 文件系统镜像构建工具（创建/列出/解包）

## 简介

mklittlefs 是 earlephilhower 维护的 LittleFS 镜像 CLI 工具，广泛用于
微控制器固件开发（ESP8266/ESP32 Arduino/PlatformIO 生态）。它将主机
目录树打包为 LittleFS 镜像，或将镜像解包回目录树，并可列出镜像内容，
常用于固件文件系统分区的离线制作与检查。

上游 4.1.0 官方发布物 `mklittlefs-source.zip` 是自包含的：zip 内捆绑
littlefs v2.11.1（commit 8e251dd675da00342d45dac78b6f627f119aed03）
与 tclap 头文件，单二进制产物，无外部依赖。

许可证：本体 MIT；捆绑的 littlefs 为 BSD-3-Clause，tclap 为 MIT。

## OHOS 适配要点

- 上游 Makefile 硬编码 g++，OHOS PC 仅 clang，通过 `CC/CXX` 环境变量注入。
- Makefile 版本号默认 `git describe`，源码 zip 无 .git，需显式传
  `VERSION=4.1.0 LITTLEFS_VERSION=v2.11.1` 保证版本确定性。
- OHOS clang 自动注入 `-Wl,--code-sign`，在 -Werror 下触发
  unused-command-line-argument，需 `-Wno-error=unused-command-line-argument`。
- strip 会去掉 .codesign 段导致二进制 Operation not permitted，
  构建用 `STRIP=true` 跳过。
- 源码 zip 顶层为 `src/`，layout 需 `folders.source/build = "src"`。

## 依赖

无外部依赖。littlefs 与 tclap 均捆绑于官方源码 zip。

## 功能验证

```bash
# 创建镜像
mklittlefs -c <input_dir> -s 1048576 output.img
# 列出镜像内容
mklittlefs -l output.img
# 解包镜像
mklittlefs -u <output_dir> -s 1048576 output.img
```

## 参考

- [源码仓库](https://github.com/earlephilhower/mklittlefs)
- [LittleFS](https://github.com/littlefs-project/littlefs)
