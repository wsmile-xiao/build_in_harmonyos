# Nestopia 1.53.2 — 本地验证报告（HarmonyOS PC / aarch64）

## 构建环境

- 目标：OpenHarmony / HarmonyOS PC，aarch64（armv8），clang 15，C++17
- Conan profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS, compiler=clang 15）
- 构建系统：autotools（`autoreconf -fi` → `configure` → `make`）

## 构建命令与结果

```
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

结果：返回码 0；`nestopia/1.53.2` 打包成功（bin/nestopia + lib/libnestopia_core.a +
include/core/** + share 资源）。核心对象归档：295 个 core 对象。

## 依赖核验（W0）

`conan download <pkg> -r=ohpcd --only-recipe` 全部通过：

| 依赖 | 版本 |
|------|------|
| zlib | 1.3.1.1（-fPIC 重建版） |
| libarchive | 3.8.7 |
| libsamplerate | 0.2.2 |
| sdl2 | 2.32.10 |
| libepoxy | 1.5.10 |
| libfltk | 1.3.11（间接 libx11/1.8.13、xorgproto/2025.1） |

## 测试执行（test_package 无头冒烟）

test_package 构建 `nestopia_core_smoke`，链接 `libnestopia_core.a`，在
HarmonyOS PC 上签名（llvm-objcopy + binary-sign-tool）后实际运行：

```
PASS nestopia core smoke: load=0 power=ok frames=3 reset_frame=1 unload=ok
```

覆盖断言（5 项）：
1. 最小 iNES ROM（16 字节头 + 16 KiB PRG + 8 KiB CHR）加载返回 RESULT_OK
2. Power(true) 上电成功
3. 执行 3 帧后帧计数 == 3
4. Reset(true) 复位后执行 1 帧帧计数 == 1
5. Power(false) 下电与 Unload 均返回 RESULT_OK

## 补丁黄金验证

三个补丁在干净基准树（tar 解压未编辑）上执行：
- `git apply --check` 全部通过
- 应用后与适配工作树 `diff=0`

| 补丁 | 内容 |
|------|------|
| 0001-configure.ac.patch | 依赖 flags 改为外部显式注入（禁用宿主 pkg-config/fltk-config 探测） |
| 0002-Makefile.am.patch | 将 fltkui_gl_ohos.cpp 纳入 nestopia_SOURCES |
| 0003-add-fltk-gl-ohos.patch | 新增 Fl_Gl_Window OHOS 符号实现（can_do()=0） |

## 已知限制（如实记录）

- OHOS 提供 EGL/GLES2 但无 GLX/桌面 OpenGL，仓内 libfltk 无 libfltk_gl.a；
  FLTK 前端显示路径无法在无头环境验证，仅完成编译链接。
- 本报告测试仅驱动 `source/core/`，不初始化 FLTK/SDL/显示。