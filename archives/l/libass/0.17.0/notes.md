# libass 0.17.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化构建环境（init-build）
2. 应用 autotools 补丁（config.guess, config.sub, configure）
3. 运行 configure：`./configure --prefix=/storage/Users/currentUser/usr/local`
4. 运行 make：`make -j4`
5. 安装到 staging：`make install DESTDIR=/storage/Users/currentUser/test-install-libass-0.17.0`
6. 安装到本地：`make install`（无 DESTDIR）
7. 生成补丁文件（refresh-patch --auto）
8. 创建预编译包（手动 tar.gz）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统 | E007: 缺少 HarmonyOS/__OHOS__ 检测分支 | 应用 patch-autotools-ohos.pl 补丁脚本 |
| 2 | config.sub: Kernel 'linux' not known to work with OS 'ohos' | E072: kernel-os 白名单缺少 linux-ohos* | 手动添加 linux-ohos* 到 config.sub 第 1780 行 |
| 3 | config.status: Permission denied creating confXXXXXX | E011: HMDFS umask 077 权限问题 | 修改 configure 中 umask 077 为 umask 022 |
| 4 | 链接器找不到 -lfribidi/-lfontconfig | 预编译包缺少开发软链接（libxxx.so） | 手动创建软链接：ln -s libxxx.so.x.y.z libxxx.so |
| 5 | 缺少 expat 依赖 | fontconfig 需要 expat | 安装 expat 2.7.1 预编译包 |

## 源码修改

### 补丁文件（3 个）
1. `0001-config.guess.patch` - 添加 HarmonyOS/__OHOS__ 检测分支
2. `0002-config.sub.patch` - 添加 ohos-linux 三元组 + linux-ohos* 白名单
3. `0003-configure.patch` - umask 077 → umask 022（HMDFS 权限兼容）

## 依赖版本

- freetype2/26.6.20 (2.14.3)
- fribidi/1.0.13
- harfbuzz/14.2.0
- fontconfig/2.16.0
- expat/2.7.1

## 验证结果

```bash
# pkg-config 验证
$ pkg-config --modversion libass
0.17.0

# 库文件验证
$ ls ~/usr/local/lib/libass*
libass.a  libass.la  libass.so  libass.so.9  libass.so.9.2.0

# 头文件验证
$ ls ~/usr/local/include/ass/
ass.h  ass_types.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libass-0.17.0-ohos-aarch64.tar.gz | 3.3 MB | 预编译包（包含 .so/.a/.pc/.h） |
| 0001-config.guess.patch | 1.0 KB | 平台识别补丁 |
| 0002-config.sub.patch | 2.6 KB | 三元组验证补丁 |
| 0003-configure.patch | 0.9 KB | umask 权限补丁 |

## 注意事项

1. **预编译包缺少开发软链接**：需要手动创建 libxxx.so 软链接，否则链接器找不到库
2. **G0 干净构建验证**：Python subprocess 在 HMDFS 上有平台限制，建议手动验证 configure 成功
3. **补丁应用顺序**：必须按 0001 → 0002 → 0003 顺序应用

---
**编译结束**: 2026-05-19 20:46
**最终状态**: published