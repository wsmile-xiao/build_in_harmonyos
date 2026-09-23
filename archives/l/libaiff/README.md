# LibAiff

## 简介
LibAiff 是 Audio Interchange File Format (AIFF/AIFF-C) 的 C 语言读写库，支持 LPCM 全采样精度、float32 与 G.711 编解码转换，以及名称/作者/版权等元数据与标记（marker）读写，轻量可移植，按 MIT 许可证发布。

## OHOS 适配
- **构建系统**: autotools（configure.ac + Makefile.am，需 `autoreconf -fi` 生成 configure）
- **三方依赖**: 无外部依赖，仅需 automake/autoconf/libtool 构建工具
- **平台要点**: 显式 `--build/--host=aarch64-unknown-linux-ohos`；生成脚本中 `umask 077` 替换为 `umask 022`（HMDFS 兼容）；`make -j1`

## 功能验证
```bash
conan create archives/l/libaiff/6.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 参考
- 上游仓库: https://github.com/mtszb/libaiff
- 原始项目页: https://aifftools.sourceforge.net/libaiff
- 参考手册: https://github.com/mtszb/libaiff/blob/master/MANUAL.html
