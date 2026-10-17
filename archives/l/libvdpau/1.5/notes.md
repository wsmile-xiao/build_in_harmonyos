# libvdpau 1.5 适配笔记

## 编译环境
- 构建系统: meson (>= 0.41, 设备侧 1.11.1)
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (OHOS SDK 15, libc++)
- 状态: published

## 软件形态（无裁剪）

libvdpau 是 VDPAU 的包装库（wrapper），架构上全部围绕 dlopen 分发：
- `libvdpau.so.1.0.0`（src/vdpau_wrapper.c, C）：应用链接 `-lvdpau`，调用
  `vdp_device_create_x11` 后按 `VDPAU_DRIVER_PATH`/`VDPAU_MODULEDIR` dlopen
  后端驱动 `libvdpau_<driver>.so.1`；`VDPAU_TRACE=1` 时再 dlopen 追踪库。
- `libvdpau_trace.so.1.0.0`（trace/vdpau_trace.cpp, C++ 5389 行）：安装到
  `lib/vdpau/`（moduledir），由 wrapper dlopen，非链接型模块。
- 头文件 `include/vdpau/{vdpau.h,vdpau_x11.h}`、`vdpau.pc`、
  `etc/vdpau_wrapper.cfg`。

上游 meson.build 对两个目标硬编码 `shared_library()`（dlopen 架构决定的），
故配方不提供 shared 选项（静态构建在架构上不可能，属设计而非裁剪）。

**功能开关全部保留**：
- `-Ddri2=true`：mesa_dri2.c 编入（通过 DRI2 扩展查询驱动名）。所需头文件
  与 pc 模块全部来自 conan：`X11/Xlibint.h`←libx11、`X11/extensions/Xext.h`
  与 `extutil.h`←libxext、`dri2proto.h/dri2tokens.h`+`dri2proto.pc`←xorgproto
  （dri2proto 上游早已并入 xorgproto，无需单独适配）。
- `-Ddocumentation=false`：仅 doxygen HTML 文档，不属于库功能（CI 无
  doxygen/dot）；cairo 等配方同款处理。

## 编译步骤

```bash
conan create archives/l/libvdpau/1.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内部：`get()` 官方 tarball → `PkgConfigDeps`+`MesonToolchain` →
`meson configure`（注入 llvm-ar/llvm-ranlib 全路径，CI PATH 上无裸名）→
`meson build` → `meson test`（上游测试）→ `meson install`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 依赖探测 x11/xext/dri2proto | 交叉/设备环境无系统 X11 | PkgConfigDeps 生成 pc；xorgproto 自带 share/pkgconfig 注入 PKG_CONFIG_PATH |
| 2 | meson 可能按裸名 llvm-ar 探测归档器 | CI PATH 不含 SDK bin | 照 libdrm 配方把 llvm-ar/llvm-ranlib 全路径写入 conan_meson_native.ini |
| 3 | musl 无 secure_getenv/__secure_getenv | OHOS libc 为 musl | 上游 util.h 内建回退 getenv_wrapper（getuid==geteuid 才返回环境变量），编译期 #warning 提示，零补丁 |
| 4 | meson install 重写 .so（剥 build rpath）→ 链接器 OHOS 自签失效 → XPM 拒绝加载（dlopen 与 DT_NEEDED 均报 Permission denied） | meson minstall 的 rpath 重写破坏 .codesign 完整性（cairo ML-0043 同场景） | package() 内 llvm-objcopy 剥旧 .codesign + binary-sign-tool -selfSign 1 重签（含 lib/vdpau 追踪模块）；实测签名后 dlopen OK |
| 5 | meson 找不到 dri2proto 依赖 | MesonToolchain 在 machine file 写死 pkg_config_path=generators 目录，meson 用它**替换**（非追加）env PKG_CONFIG_PATH（mesonbuild pkgconfig.py _get_env: env.set），xorgproto 经 buildenv_info 注入的 share/pkgconfig 被遮蔽 | generate() 后处理 conan_meson_native.ini：pkg_config_path 改写为列表 [generators, 各依赖自有 pkgconfig 目录]，conan 生成的 pc 保持优先 |
| 6 | trace/vdpau_trace.cpp 报 X11/Xlib.h not found | 上游 trace/meson.build 未声明 x11 依赖（依赖系统头文件默认路径），meson 只给声明了依赖的目标传 -I | patches/0001：trace 目标 dependencies 改 [libdl, x11]（x11 变量在 src/meson.build 已定义，meson subdir 共享变量作用域） |
| 7 | meson test 默认 conanbuild 环境缺 host 依赖 libdir → dlclose 测试在第一步 dlopen(libXext) 即跳过 | conanbuild 不携带 host 依赖 libdirs | generate() 增加 VirtualRunEnv，build() 用 `self.run('meson test -v …', env='conanrun')` → 测试真实走到 XOpenDisplay 才跳过 |

## 上游测试清点与实测（R51 三步法）

**清点**（`meson test --list`，源码 test/ 目录）：
- 上游全部测试 = 1 项：`dlclose`（test/dlclose.c）
  内容：dlopen("src/libvdpau.so") + dlopen("libXext.so.6") + XOpenDisplay +
  vdp_device_create_x11 + dlclose，前后比对 /proc/self/fd 计数，防 fd 泄漏回归。

**可运行性**（已实测）：
- `meson test`（以 conanrun 环境运行，LD_LIBRARY_PATH 含全部依赖 libdir）：
  dlopen("libXext.so.6") 成功 → dlopen("src/libvdpau.so") 成功（包装库真实
  加载，DT_NEEDED libX11.so.6 解析成功）→ XOpenDisplay(NULL) 返回 NULL →
  测试程序**自身** return SKIP(77)，meson 汇报 `Ok:0 Fail:0 Skipped:1`，
  test() 通过。stderr: "Failed to connect to X display"。
- 有 X11 server 的环境：可完整跑（本平台无此环境，如实记录）。

**test_package**（消费者视角，conan test 自动执行）：
- 链接真实 libvdpau.so，调用唯一导出符号 `vdp_device_create_x11`：
  setenv VDPAU_DRIVER=不存在的驱动 → 断言返回 VDP_STATUS_NO_IMPLEMENTATION
  （完整走通 env 读取→路径拼装→dlopen 尝试→错误回传链路）+ 头文件版本断言。
- CI L1e 反向破坏验证：移除包 lib/ 后链接必失败（真实依赖被测包）。

## 依赖版本

- libx11/6.4.0（x11.pc, Xlibint.h, libX11.so.6）
- libxext/6.4.0.1（xext.pc, Xext.h, extutil.h, libXext.so.6；其自身
  精确 pin libx11/6.4.0，属 6.4.x ABI 家族）
- xorgproto/2025.1（dri2proto.pc + dri2{proto,tokens}.h）

## 验证结果（实测）

```bash
conan create archives/l/libvdpau/1.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# → exit 0
# meson test: Ok:0 Fail:0 Skipped:1（dlclose 无 X server，上游自身 return 77）
# test_package: libvdpau wrapper dlopen dispatch OK: status=1 (no backend, as expected)
# 包内容: lib/libvdpau.so{,.1,.1.0.0}(SONAME=libvdpau.so.1) lib/vdpau/libvdpau_trace.so*
#         include/vdpau/{vdpau.h,vdpau_x11.h} lib/pkgconfig/vdpau.pc etc/vdpau_wrapper.cfg
# 全部 .so 经 binary-sign-tool 自签，dlopen 实测通过
```

## 源码修改

patches/0001-trace-declare-x11-dependency.patch（1 行，可移植性修复，
非平台裁剪）：trace/meson.build 的 `dependencies : libdl` →
`dependencies : [libdl, x11]`。vdpau_trace.cpp 经 vdpau_x11.h 间接包含
X11/Xlib.h，上游未声明该依赖（假定系统头文件在默认搜索路径）。

## 注意事项

- 运行时：包装库按 `VDPAU_MODULEDIR`（编译期 = ${prefix}/lib/vdpau，conan
  安装后即包内路径）或 `VDPAU_DRIVER_PATH` 查找后端驱动；真机使用时由
  GPU 厂商驱动（如 libvdpau_nvidia.so.1）放置于该目录或经环境变量指定。
- lib/vdpau/libvdpau_trace.so* 是 dlopen 模块，不出现在 cpp_info.libs，
  但随包分发（上游 moduledir 安装布局）。
- meson install 后必须重签 .so（见问题表 #4），否则 OHOS 加载器拒绝加载。
## 对话记录

### 对话 #1 — conan 配方驱动适配（2026-09-18）

- conan-init 生成骨架（autotools 模板）→ 按 libdrm/cairo 参考改写为 meson 配方
- 第 1 次失败：`package_type="library"` 无 shared 选项 → 改 `shared-library`
- 第 2 次失败：meson 找不到 dri2proto（MesonToolchain 写死 pkg_config_path 遮蔽
  xorgproto 的 buildenv_info 注入路径）→ 后处理 conan_meson_native.ini 改为路径列表
- 第 3 次失败：trace/vdpau_trace.cpp 找不到 X11/Xlib.h（上游漏声明 x11 依赖）
  → patches/0001 补丁 1 行修复
- 第 4 次失败：test_package 报 "Error loading shared library libvdpau.so.1"
  （meson install 重写 .so 使链接器自签失效）→ package() 内
  llvm-objcopy 剥旧 .codesign + binary-sign-tool -selfSign 1 重签
- 第 5 次调整：meson test 默认 conanbuild 环境缺 host 依赖 libdir →
  generate() 加 VirtualRunEnv，build() 以 env="conanrun" 跑 meson test，
  上游 dlclose 测试真实走到 XOpenDisplay 才 SKIP(77)
- 第 6 次修正：手写补丁 hunk 行数错误（@@ -1,6 实为 10 行）导致 G0
  clean-verify 补丁应用失败 → 用 git diff --no-index 重新生成
- 最终：conan create exit 0；conan-verify G0-G4+L2/L4/L5 全过；
  W3 本地 CI（JC/L0/L1/L4/L5）全过，Success 1/Failed 0

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml + patches/0001 | Conan 配方（CI 输入） |
| test_package/{conanfile.py,test.c,CMakeLists.txt,MANIFEST.yml} | 消费者测试（CI 输入） |
| lib/libvdpau.so.1.0.0（SONAME libvdpau.so.1） | 包装库（已自签） |
| lib/vdpau/libvdpau_trace.so.1.0.0 | dlopen 追踪模块（已自签） |
| include/vdpau/{vdpau.h,vdpau_x11.h} | 公共头文件 |
| lib/pkgconfig/vdpau.pc / etc/vdpau_wrapper.cfg | pkg-config 描述 / 运行时配置 |
---

**编译结束**: 2026-09-18 18:32
**最终状态**: built（conan-verify + W3 全过；upload 待 PR 合并后 release 流水线执行）
