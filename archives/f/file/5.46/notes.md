# file 5.46 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **初始化**: `ohc-run.py init-build file 5.46`
2. **平台适配**:
   - 使用 hints/config.guess 替换（HarmonyOS 平台识别）
   - 使用 hints/config.sub 替换（linux-ohos 三元组支持）
3. **Configure**: `./configure --prefix=$DEFAULT_PREFIX --disable-shared`
4. **编译**: `make -j2`
5. **安装**: `make install DESTDIR=$TEST_PREFIX`
6. **打包**: `ohc-run.py package file 5.46`
7. **验证**: `ohc-run.py verify-build file 5.46`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | autotools 未包含 HarmonyOS 识别 | 使用 hints/config.guess 替换文件 |
| 2 | config.sub 不接受 linux-ohos | 内核验证列表缺少 linux-ohos | 使用 hints/config.sub 替换文件 |
| 3 | 动态库加载失败 | HarmonyOS 动态链接器不信任 ~/usr/local/lib | 使用 `--disable-shared` 静态编译 |
| 4 | configure 临时目录权限错误 | hmdfs + umask 077 导致目录不可访问 | 在 configure 中设置 umask 022（已记录为平台限制，不补丁） |

## 平台适配方案（符合 R6/R23 铁律）

使用 **hints 目录** 替代补丁：
- `hints/config.guess`: HarmonyOS 平台识别（aarch64-unknown-linux-ohos）
- `hints/config.sub`: linux-ohos 三元组支持

此方案符合 R6（不修改生成文件）和 R23（使用 hints 机制）。

## 依赖版本

- 无外部依赖（纯 C 实现）

## 验证结果

```bash
$ ~/usr/local/bin/file --version
file-5.46
magic file from /storage/Users/currentUser/usr/local/share/misc/magic

$ ~/usr/local/bin/file ~/usr/local/bin/file
/storage/Users/currentUser/usr/local/bin/file: ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, with debug_info, not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| file-5.46-ohos-aarch64.tar.gz | 11MB | 预编译包 |
| file-5.46-ohos-aarch64-debug.tar.gz | 370KB | 调试符号包 |

## 注意事项

- **必须使用静态编译**（`--disable-shared`），否则动态库无法加载
- hmdfs 临时目录问题已记录，后续 autotools 软件需注意
- 预编译包已包含 ELF 签名

---
**编译结束**: 2026-05-19 18:12
**最终状态**: built