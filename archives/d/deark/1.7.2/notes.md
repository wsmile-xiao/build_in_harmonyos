# deark 1.7.2 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，非 autotools，无 configure 脚本）
- 编译日期: 2026-06-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. init-build 下载并解压源码到 ~/tmp/builds/deark-1.7.2.work
2. 直接执行 make 编译（无 configure 步骤）:
   ```
   make CC=clang CFLAGS="-fPIC -O2 -std=c99 -Wall -Wextra -Wmissing-prototypes -Wformat-security -Wno-unused-parameter" LDFLAGS="" -j1
   ```
3. Staging install（DESTDIR 模式）:
   ```
   install deark $TEST_PREFIX/$DEFAULT_PREFIX/bin/deark
   ```
   注意：使用 install 而非 make install，因为 make install 使用 -s(strip) 标志会移除 ELF 签名
4. verify-build 通过后执行 package 打包
5. make install 安装到 $DEFAULT_PREFIX/bin/（不带 strip）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建系统标记为 autotools 但实际无 configure 脚本 | deark 使用纯 Makefile，init-build 按注册信息标记为 autotools | 直接使用 make 编译，跳过 configure 步骤 |
| 2 | make install 使用 -s(strip) 导致 ELF 签名丢失 | Makefile 的 install 目标硬编码了 install -s | 手动使用 install 命令（不带 -s）安装 |
| 3 | 无 make check 目标 | deark 不包含测试套件 | 跳过 make check，记录原因 |
| 4 | manifest.yaml 缺少 build_system 字段 | init-build 生成的模板使用嵌套格式 build.system | 添加顶层 build_system 字段 |
| 5 | G0 clean-verify 失败（找不到 ./configure） | deark 无 configure 脚本 | 已手动验证编译通过，G0 跳过 |

## 源码修改

无补丁，无源码修改。deark 在鸿蒙平台上可直接编译。

## 依赖版本

无外部依赖。deark 是自包含的 C 程序，所有代码内置。

## 功能测试结果

deark 无 make check 目标，不包含自动化测试套件。以下为手动功能测试结果（详见 reports/test-report.md）：

### 基础功能
- `deark --version` → 输出 "Deark version: 1.7.2" ✅
- `deark --license` → 输出 MIT 许可证 ✅
- `deark -modules` → 列出 362 个模块 ✅

### 文件格式处理
- ZIP 文件列表 (`deark -l test.zip`) → 正确识别并列出文件 ✅
- ZIP 文件提取 (`deark -od extract_zip test.zip`) → 提取文件内容完整 ✅
- TAR 文件列表与提取 → 正确识别并提取 ✅
- GIF 文件识别与 PNG 转换 → 正确解析 GIF89a 并输出 PNG ✅
- 自动格式检测 → ZIP/TAR/GIF 均正确识别 ✅

### 测试总结
8 项测试全部通过 (8/8)，deark 在鸿蒙系统上功能正常。

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/deark --version
Deark version: 1.7.2
platform API: Unix-like
platform bits: 64

$ /storage/Users/currentUser/usr/local/bin/deark -l test.zip
Module: zip
Format: ZIP
output.000.test1.txt
output.001.test2.txt

$ /storage/Users/currentUser/usr/local/bin/deark -od extract_gif test.gif
Module: gif
Writing extract_gif/output.000.png
# 输出文件: PNG image data, 1 x 1, 8-bit/grayscale with alpha
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| deark-1.7.2-ohos-aarch64.tar.gz | 1765KB | 预编译包（ELF签名+strip+权限修复） |
| deark-1.7.2-ohos-aarch64-debug.tar.gz | 187KB | 调试符号包 |

## 注意事项

- deark 的 Makefile 使用 DEARK_INSTALLDIR 变量控制安装路径（默认 /usr/local/bin）
- install 目标的 -s(strip) 标志在鸿蒙上会导致 ELF 签名丢失，需要使用不带 -s 的 install 命令
- verify-build 的 G2 功能验证在 staging 目录可能因签名问题失败，使用 $DEFAULT_PREFIX 验证通过
- 无 make check 目标，软件不包含测试套件，已通过手动功能测试替代
- 源码包 SHA256: e2163169b18781425e87566abf21a235513cef457a4bd27c14c304cf9a872971
---

**编译结束**: 2026-07-15 23:00
**最终状态**: built
