# x264

## 简介

x264 是一个开源的视频编码库，用于将视频流编码为 H.264/MPEG-4 AVC 格式，广泛应用于视频处理和流媒体领域。它同时提供 `libx264` 库与 `x264` 命令行编码器。

上游仓库：https://code.videolan.org/videolan/x264 （许可：GPL-2.0-or-later）

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| r3223 | built | 2026-09-13 | Conan 配方；源码按提交 SHA 固定；上游 checkasm 102/102 通过 |
| r3190 | published（历史条目，无配方） | 2026-05-20 | 早期尝试，目录内无 conanfile.py，不在制品仓 |

## OHOS 适配

- **构建系统**：x264 使用**手写 configure**（非 autoconf 产物），流程为 `bash ./configure && make && make install`
- **shebang**：configure 首行是 `#!/bin/bash`，OHOS 上不存在 `/bin/bash`，须用 hnp 的 bash 显式执行
- **平台判定**：自带 config.guess 不认识 OHOS，显式传 `--host=aarch64-unknown-linux-gnu`
- **汇编**：aarch64 分支的汇编器就是 clang（`AS="${AS-${CC}}"`），**不需要 nasm/yasm**
- **install**：OHOS 无 coreutils `install`，但 `/bin/install`（toybox）支持 `-d`/`-m`，故上游 install 规则可原样使用
- **PIC**：使用 `--enable-pic` 生成位置无关代码
- **签名**：`.so` 与可执行文件在鸿蒙 PC 上需代码签名，打包末尾统一用 `binary-sign-tool` 重签
- **版本串**：SHA 归档不含 `.git`，上游 `version.sh` 退化会把版本串变成 `0.165.x`；配方按固定提交回填为 `0.165.3223`

## 依赖

无外部依赖，为基础库（x264 本身的第三方依赖为零）。

## 功能验证

```bash
pkg-config --modversion x264
# 输出: 0.165.3223

x264 --version
# 输出: x264 0.165.3223
```

上游自带测试（汇编内核自检）：

```bash
make checkasm && ./checkasm8 && ./checkasm10
# checkasm8  66 项 [OK] / 0 [FAIL]
# checkasm10 36 项 [OK] / 0 [FAIL]
# x264: All tests passed Yeah :)
```

## 参考

- 官网: https://www.videolan.org/developers/x264.html
- 源码: https://code.videolan.org/videolan/x264
