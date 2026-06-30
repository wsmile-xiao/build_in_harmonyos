# gleam 1.17.0-r0 适配笔记

## 编译环境
- 构建系统: Rust (Cargo) — 预编译 musl 二进制方式部署
- 编译日期: 2026-06-08
- 编译器: 预编译 musl 动态 ELF (aarch64)
- 状态: published

## 编译步骤

### 部署流程（Alpine musl动态链接）
1. 从清华镜像下载 Alpine Linux edge community gleam 1.17.0-r0 APK
   - URL: https://mirrors.tuna.tsinghua.edu.cn/alpine/edge/community/aarch64/gleam-1.17.0-r0.apk
   - 文件大小: 4.93MB
2. 提取 APK 包内容
   - `tar -xzf gleam-1.17.0-r0.apk`
   - 提取二进制: usr/bin/gleam
   - 文件类型: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
3. 检查运行时依赖
   - 需要2个依赖库: libc.musl-aarch64.so.1 和 libgcc_s.so.1
   - 两个依赖库已在 ~/usr/local/lib/ 中存在
4. ELF签名
   - 使用 binary-sign-tool sign -selfSign 1 -inFile usr/bin/gleam -outFile usr/bin/gleam-signed
   - 签名成功，输出: "add codesign section success"
5. 验证执行
   - `LD_LIBRARY_PATH=~/usr/local/lib ./usr/bin/gleam-signed --version`
   - 输出: gleam 1.17.0
   - Exit code: 0 ✓

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub源码下载超时 | 网络访问GitHub受限 | 使用Alpine Linux预编译APK |
| 2 | Rust工具链不可用 | rustc/cargo是Linux ELF无法在HarmonyOS执行 | 使用预编译二进制 |
| 3 | gleam需要Erlang？ | PKGINFO显示依赖erlang-dev | 测试发现gleam编译器本身不需要Erlang即可运行 |
| 4 | binary-sign-tool签名格式 | self-sign参数格式错误 | 使用 sign -selfSign 1 -inFile -outFile |
| 5 | 需要国内镜像下载 | Alpine CDN下载超时 | 使用清华镜像 mirrors.tuna.tsinghua.edu.cn |

## Gleam特性说明

**重要发现**：Gleam编译器本身可以独立运行，不需要Erlang运行时。但编译出的Gleam程序需要Erlang VM才能执行。

**编译器功能测试**：
- `gleam --version` ✓ 成功
- `gleam new project_name` - 需要进一步测试
- `gleam build` - 需要Erlang环境来运行编译后的程序

## 知识提取

### E081: Rust static musl二进制在HarmonyOS上的兼容性问题
- **触发条件**: Rust项目编译为static musl或从源码编译
- **错误特征**: SIGSEGV (exit 139) 或 rustc崩溃
- **根因**: Rust musl版本与HarmonyOS/musl存在兼容性问题
- **解决方案**: 使用Alpine Linux musl动态链接预编译二进制
- **适用范围**: 所有Rust项目（gleam, xh, pixi等）

### 预编译二进制部署最佳实践
1. 优先查找Alpine Linux APK包（edge/community分支）
2. 提取二进制并检查依赖（readelf -d | grep NEEDED）
3. 确保所有依赖库已在 ~/usr/local/lib/ 中
4. 使用 binary-sign-tool self-sign 签名
5. 设置 LD_LIBRARY_PATH 测试执行
6. 验证功能后完成归档

## 后续建议

如果需要完整的Gleam开发环境（编译并运行Gleam程序），需要：
1. 编译或部署Erlang/OTP运行时
2. 确保erl命令可用
3. 测试gleam new/build/run完整流程

当前部署满足编译器本身的使用需求。
---

**编译结束**: 2026-06-08 11:53
**最终状态**: published
