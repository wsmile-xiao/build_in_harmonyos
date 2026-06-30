# libxrandr 1.5.5 适配笔记

## 编译环境
- 构建系统: autotools/meson（源码支持两种构建系统）
- 编译日期: 2026-05-22
- 编译器: clang 15.0.4
- 状态: failed

## 编译步骤

1. **下载源码**: 从X.org官方下载libXrandr-1.5.5.tar.gz
   - URL: https://www.x.org/releases/individual/lib/libXrandr-1.5.5.tar.gz
   - 版本: 1.5.5（2026-01-26发布）

2. **初始化编译环境**:
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build libxrandr 1.5.5 --url=file://$HOME/tmp/libXrandr-1.5.5.tar.gz
   ```

3. **尝试meson构建**: 遇到依赖缺失问题
   - meson无法找到x11依赖
   - 缺少libX11、libXext、libXrender等核心X11库

4. **尝试autotools构建**:
   ```bash
   ./configure --prefix=/storage/Users/currentUser/usr/local
   ```
   - 首次失败：config.guess无法识别HarmonyOS系统（E007）
   - 修复config.guess/config.sub后重新运行
   - 仍然失败：缺少libX11等核心依赖

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | meson无法找到x11依赖 | libX11未安装，cmd-pkgs无预编译包 | 需手动编译libX11 | ❌ 未解决 |
| 2 | config.guess无法识别HarmonyOS | GNU config.guess不包含__OHOS__检测 | 使用patch-autotools-ohos.pl修复 | ✅ 已解决 |
| 3 | 缺少libX11依赖链 | X11库依赖链复杂，无预编译包 | 需按顺序编译: libxcb→libX11→libXext→libXrender→libXrandr | ❌ 未解决 |

## 核心依赖缺失

### 缺少的依赖库（按编译顺序）
1. **libxcb** - X C绑定库（libX11的基础依赖）
   - 进一步依赖: libxau, libxdmcp
   - cmd-pkgs状态: ❌ 无预编译包

2. **libX11** - X11客户端库
   - 依赖: libxcb, xorgproto
   - xorgproto已通过预编译包安装 ✅
   - cmd-pkgs状态: ❌ 无预编译包

3. **libXext** - X扩展库
   - 依赖: libX11
   - cmd-pkgs状态: ❌ 无预编译包

4. **libXrender** - X渲染库
   - 依赖: libX11
   - cmd-pkgs状态: ❌ 无预编译包

### 已安装的依赖
- **xorgproto 2024.1** ✅ (通过预编译包安装)
  - 包含randrproto, renderproto, xextproto等协议定义
  - pkg-config文件位于: /storage/Users/currentUser/usr/local/share/pkgconfig/

## 失败原因分析

**主要原因**: 缺少核心X11库依赖链，且cmd-pkgs中没有这些库的预编译包

**具体原因**:
1. libXrandr属于X.org库家族，依赖完整的X11基础设施
2. X11库在鸿蒙平台上较少使用，因此cmd-pkgs中缺少预编译包
3. 手动编译需要完整的依赖链（libxcb→libX11→libXext→libXrender），工作量较大

**遵循R18原则**:
- ✅ 已检查cmd-pkgs预编译包列表（561个包）
- ✅ 已安装可用的预编译包（xorgproto）
- ❌ 核心依赖libX11等无预编译包，需手动编译

## 源码修改

### 修改文件
1. **config.guess** - 添加HarmonyOS/__OHOS__检测分支
   - 使用patch-autotools-ohos.pl自动修复

2. **config.sub** - 添加ohos-linux三元组支持
   - 使用patch-autotools-ohos.pl自动修复

## 验证结果

```bash
# config.guess修复验证
$ ./config.guess
aarch64-unknown-linux-ohos  ✅

# proto包验证
$ export PKG_CONFIG_PATH="/storage/Users/currentUser/usr/local/lib/pkgconfig:/storage/Users/currentUser/usr/local/share/pkgconfig"
$ pkg-config --modversion randrproto
1.6.0  ✅

# configure失败信息
$ ./configure --prefix=/storage/Users/currentUser/usr/local
...
checking for RANDR... no
configure: error: Package requirements (x11 >= 1.6 randrproto >= 1.5 xext xextproto xrender renderproto) were not met:
No package 'x11' found  ❌
No package 'xext' found  ❌
No package 'xrender' found  ❌
```

## 交付物

无（编译失败）
**失败原因**: 缺少核心X11库依赖（libX11/libXext/libXrender），cmd-pkgs无预编译包，需手动编译完整依赖链
---

## cmake 构建尝试（2026-05-22）

### cmake 方式验证
根据任务要求，必须使用 cmake 编译方式而非 autotools（因 HMDFS SELinux 权限限制）。

**尝试过程**:
1. 创建 CMakeLists.txt（源码原本无 cmake 支持）
2. 配置 cmake:
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
   ```
3. 结果：失败，缺少 x11 依赖
   ```
   CMake Error: The following required packages were not found:
   - x11>=1.6
   ```

### meson 构建尝试
源码自带 meson.build，尝试使用 meson 构建：
```bash
meson setup build-meson --prefix=$DEFAULT_PREFIX
```
结果：失败，缺少 x11 依赖
```
Run-time dependency x11 found: NO
ERROR: Dependency "x11" not found
```

### 依赖分析
**已有依赖**:
- xcb ✅ (pkg-config 可找到)
- xcb-proto ✅ (1.17.0)
- xproto/xorgproto ✅ (7.0.31, randrproto 1.6.0)

**缺失依赖** (需手动编译):
- libX11 (依赖 xcb, xproto - 已满足)
- libXext (依赖 libX11)
- libXrender (依赖 libX11)

**编译顺序建议**:
```
1. libX11 1.8.13 (基础)
2. libXext (扩展库)
3. libXrender (渲染库)
4. libXrandr (目标)
```

### 结论
- cmake 方式已验证，因依赖缺失失败
- meson 方式同样失败
- 需要编译完整的 X11 依赖链（libX11→libXext→libXrender→libXrandr）
- cmd-pkgs 中无 libX11 系列的预编译包

---
**编译结束**: 2026-05-22 14:55
**最终状态**: failed

**二次编译结束**: 2026-05-22 17:30
**最终状态**: failed (依赖缺失)
---

**编译结束**: 2026-05-25 10:53
**最终状态**: built
