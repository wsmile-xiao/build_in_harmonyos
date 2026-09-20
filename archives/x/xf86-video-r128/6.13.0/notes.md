# xf86-video-r128 6.13.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-08（首次）/ 2026-09-17（Conan 配方修复）
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
source /storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/.build-context-xf86-video-r128-6.13.0

export PKG_CONFIG_PATH="/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig:$PKG_CONFIG_PATH"

cd $BUILD_SRC_DIR

./configure --prefix=$DEFAULT_PREFIX \
  --disable-dri --disable-exa \
  SED=/storage/Users/currentUser/usr/local/bin/sed \
  HELP2MAN=/bin/true \
  MAKEINFO=/bin/true \
  CC=clang CFLAGS="-fPIC -O2" \
  LDFLAGS="-L/storage/Users/currentUser/usr/local/lib" \
  CPPFLAGS="-I/storage/Users/currentUser/usr/local/include"

make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "cannot guess build type" | config.guess/config.sub 不识别 HarmonyOS 平台 | 修改 config.guess: UNAME_SYSTEM 添加 HarmonyOS case；aarch64 machine 添加 aarch64:HarmonyOS 映射。修改 config.sub: 添加 harmonyos* → kernel=linux,os=musl |
| 2 | configure 创建临时目录失败 (Permission denied) | HMDFS 上 umask 077 + mktemp 创建的目录不可写 | 在 config.guess 和 configure 中对 HarmonyOS 跳过 umask 077，直接用 mktemp -d |
| 3 | r128_driver.c 编译错误: BIOSseg/xf86int10Addr 未定义 | OHOS xf86int10.h 是 stub，不定义 BIOSseg 和 xf86int10Addr | 用 #ifdef __OHOS__ 守卫跳过 Int10 BIOS 读取代码块，让驱动 fall through 到 PCI ROM 路径 |
| 4 | r128_crtc.c/r128_exa_render.c 大量 DRI/EXA 错误 | OHOS xorg-server 不提供 DRI/EXA 支持 | configure 使用 --disable-dri --disable-exa 禁用 DRI/EXA 代码编译 |
| 5 | configure 找不到 xorgproto 依赖 | PKG_CONFIG_PATH 缺少 /storage/Users/currentUser/usr/local/share/pkgconfig | 安装 xorgproto 2024.1 预编译包并扩展 PKG_CONFIG_PATH |
| 6 | CI: r128.h:41 fatal error 'xf86str.h' not found | 旧配方在 build() 内下载 xorg-server 源码提取 SDK 头，但 x.org 发布的是 .tar.xz 而 tarfile.open 用 mode="r:gz" → "not a gzip file"，提取失败后仅剩合成头 | tarfile 解压用 mode="r:*"（自动识别 xz/gz）；下载多镜像 fallback（www.x.org / xorg.freedesktop.org / uwaterloo 镜像）+ sha256 校验 |
| 7 | CI: xf86Crtc.h / damage.h 等逐个缺失 | 旧提取逻辑保留子目录结构后靠全目录 -I 注入，need_dirs 白名单不全且依赖逐轮 CI 试错 | 改为按真实 SDK 布局**扁平**复制到 sdkdir（xorg-server 的 SDK 安装本身就是扁平的），一次到位 |
| 8 | configure 需要 pciaccess.pc | PkgConfigDeps 按 conan 包名生成 libpciaccess.pc，上游探测 pciaccess | build() 中复制生成 pciaccess.pc 别名（内容指向 conan 包真实路径） |
| 9 | SDK 头互相包含 <xorg-config.h> / <xkb-config.h> 失败 | 这两个 + dix-config.h / xorg-server.h 均由 xorg-server configure 生成，源码包只有 .in 模板 | conanfile 按模板最小合成四个生成头（aarch64/libpciaccess 取值） |
| 10 | proto 依赖（xproto/fontsproto/randrproto 等 29 个 .pc） | conan 只有整包 xorgproto.pc | xorgproto 配方的 package_info 已把包内 share/pkgconfig 挂到 buildenv_info；配方内显式把该目录加入 PKG_CONFIG_PATH |

## 依赖方案（2026-09-17 重构）

| 依赖 | 版本 | 来源 |
|------|------|------|
| xorgproto | 2025.1 | ohpcd conan registry（提供全部 proto 头与 .pc） |
| pixman | 0.46.4.3 | ohpcd conan registry |
| libpciaccess | 0.19 | ohpcd conan registry（2026-09-10 发布，替代旧 cmd-pkgs 0.17 方案） |
| xorg-server SDK | 21.1.15 | 无 conan 包（仅 cmd-pkg Xvfb 二进制）。build() 下载官方源码包，提取 SDK 头到 build 私有前缀，合成 xorg-server.pc 与生成头 |

构建期网络下载仅 xorg-server 官方源码包（sha256 校验、三镜像 fallback），其余依赖全部走 conan registry，
不再使用 build() 内下载 cmd-pkgs tarball 的旧方案。

## 源码修改

以下文件被修改并保存为 patch 文件：

### config.guess (0001-config.guess.patch)
- HMDFS 临时目录修复，HarmonyOS 上跳过 umask 077
- UNAME_SYSTEM 检测添加 HarmonyOS/OpenHarmony case
- aarch64:HarmonyOS 和 aarch64_be:HarmonyOS machine pattern 映射

### config.sub (0002-config.sub.patch)
- 添加 harmonyos* case pattern → kernel=linux, os=musl

### configure (0003-configure.patch)
- HMDFS 临时目录创建修复，HarmonyOS 上跳过 umask 077

### src/r128_driver.c (0004-src-r128_driver.c.patch)
- 用 #ifdef __OHOS__ 守卫跳过 pInt10->BIOSseg 和 xf86int10Addr() 调用

## 上游测试清点（R51）

- 上游 xf86-video-r128 6.13.0 无测试套件：源码树无 tests/ 目录、无 ctest/pytest 注册
- `make check` 实际输出：`Nothing to be done for 'check'`（man/ 与顶层目录均无 check 目标动作）
- test_package 采用消费者视角验证：模块存在 + ELF64 ET_DYN + 导出 r128ModuleData 模块入口

## 验证结果（conan create，CI 同 profile）

```bash
conan create archives/x/xf86-video-r128/6.13.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → Package built; test_package: All tests passed
# r128_drv.so 88448 bytes, ELF64 ET_DYN, r128ModuleData 已导出
```

编译警告（非致命，与上游一致）: r128_crtc.c unused variables / void pointer arithmetic (GNU extension)、
r128_cursor.c void pointer arithmetic、r128_output.c format string not literal。

## 交付物

| 文件 | 说明 |
|------|------|
| r128_drv.so | ATI Rage 128 Xorg 驱动模块（安装到 lib/xorg/modules/drivers/） |
| r128_drv.la | libtool 链接描述文件 |
| r128.4 | man page |

## 注意事项

- 此驱动在 OHOS 上不支持 DRI (Direct Rendering Infrastructure) 和 EXA 加速架构，仅提供基本帧缓冲支持
- Int10 BIOS 读取功能在 OHOS 上不可用（xf86int10.h 为 stub），驱动将使用 PCI ROM 路径读取 VBIOS
- HMDFS 文件系统的 umask 077 + mktemp 问题会影响所有使用此模式的 autotools 项目
- xorg-server 若未来发布 conan 包，应将 SDK 提取逻辑替换为 `self.requires("xorg-server/...")`
---

**编译结束**: 2026-09-17 13:05
**最终状态**: built
