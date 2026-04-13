# boxes 2.3.1 编译进度

**日期**: 2026-04-13
**状态**: ✅ 编译成功

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 源码下载完成 |
| Step 2 patches | ✅ | 修改 Makefile 和 boxes.c |
| Step 3 configure | ⏭️ | boxes 使用 Makefile，无需 configure |
| Step 4 make | ✅ | 编译成功 |
| Step 5 install | ✅ | boxes 可执行文件生成 |
| Step 6 safety | ⏭️ | 跳过（无需 strip） |
| Step 7 check | ⏭️ | 跳过（执行环境不支持） |
| Step 8 staging | ⏳ | 待完成 |
| Step 9 package | ⏳ | 待完成 |
| Step 10 deploy | ⏳ | 待完成 |
| Step 11 finish | ⏳ | 待完成 |

## 发现与知识

### 问题 1: libunistring configure 无法识别 HarmonyOS
**症状**: configure 遇到 socklen_t 类型检测失败
**原因**: 
1. HarmonyOS SDK 使用 musl libc 风格的头文件
2. configure 检测逻辑与 SDK 的类型定义机制冲突
**解决方案**: 
1. 更新 config.guess 和 config.sub
2. 创建 config.cache 预置检测结果
3. 修改 config.status 使用可写临时目录

### 问题 2: PCRE2 configure 无法识别 HarmonyOS
**症状**: config.sub 报错 "OS 'ohos' not recognized"
**解决方案**: 更新 config.guess 和 config.sub，指定 build 类型为 aarch64-unknown-linux-gnu

### 问题 3: ncurses 编译困难
**症状**: ncurses configure 创建乱码目录，Makefile 生成失败
**解决方案**: 修改 boxes.c 绕过 ncurses 依赖，使用 stub 函数

### 问题 4: boxes 编译器不匹配
**症状**: Makefile 硬编码 gcc
**解决方案**: 修改 src/Makefile 使用 `CC ?= gcc` 允许环境变量覆盖

### 问题 5: strip 命令缺失
**症状**: strip 命令找不到
**解决方案**: 使用 llvm-strip 手动 strip

## 依赖库编译结果

| 库 | 版本 | 状态 | 安装位置 |
|----|------|------|----------|
| libunistring | 1.0 | ✅ | vendor/libunistring-1.0/ohos-install |
| PCRE2 | 10.40 | ✅ | vendor/pcre2-10.40/ohos-install |
| ncurses | 6.4 | ⏭️ | 跳过，使用 stub |

## 编译产物

- **可执行文件**: /storage/Users/currentUser/builds/boxes-2.3.1.work/out/boxes
- **文件类型**: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
- **文件大小**: 383536 bytes (stripped)

## 代码修改摘要

1. **boxes.c**: 添加 HarmonyOS 兼容性代码，stub ncurses 函数
2. **src/Makefile**: 修改 CC 变量、添加 include/lib 路径、移除 ncurses 链接
3. **vendor/libunistring-1.0/config.cache**: 预置检测结果
4. **vendor/libunistring-1.0/config.status**: 修改临时目录路径
5. **vendor/pcre2-10.40/config.status**: 修改临时目录路径

## 下一步

1. 创建预编译包
2. 更新 manifest.yaml
3. 彐档编译产物
---

**编译结束**: 2026-04-13 18:52
**最终状态**: partial
