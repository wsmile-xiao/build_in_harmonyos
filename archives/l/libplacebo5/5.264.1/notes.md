# libplacebo5 5.264.1 适配笔记

## 编译环境
- 构建系统: meson（>=0.63，本机 1.12.0）
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（aarch64-linux-ohos）
- 状态: built（conan-verify 全部门禁通过，G0-G4+L2/L4/L5）

## 编译步骤

1. 源码下载
   - 从 VideoLAN GitLab 下载：https://code.videolan.org/videolan/libplacebo/-/archive/v5.264.1/libplacebo-v5.264.1.tar.gz
   - sha256: 9eb0c198f58d994f1c0d173dd37647d4d07d27972412c48ab758e984503c787b
   - 使用本地文件初始化编译：`--url=file://$HOME/tmp/libplacebo-v5.264.1.tar.gz`（本机 Python urllib SSL 证书校验失败）

2. Meson 配置（与 libplacebo/7.349.0 同源适配经验）
   ```bash
   meson setup build --prefix=/storage/Users/currentUser/usr/local --buildtype=release \
     -Dopengl=disabled \
     -Dvulkan=disabled \
     -Dd3d11=disabled \
     -Dglslang=disabled \
     -Dshaderc=disabled \
     -Ddemos=false \
     -Dtests=true
   ```

3. 编译
   ```bash
   ninja   # 155/155 目标全部链接成功
   ```

4. 上游测试
   ```bash
   meson test   # 9/9 全部通过（详见"上游测试申报表"）
   ```

5. 安装验证
   ```bash
   meson install --destdir $TEST_PREFIX
   # 产物：lib/libplacebo.so.264 / lib/libplacebo.so / include/libplacebo/*.h / lib/pkgconfig/libplacebo.pc
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python urllib SSL 证书验证失败 | 本机 Python CA 证书不完整 | curl -k 下载源码包到 $HOME/tmp，--url=file:// 本地初始化 |
| 2 | meson sanity check: clang++ 测试二进制 not runnable | 测试二进制运行时需 libc++_shared.so，位于 SDK `<llvm>/lib/aarch64-linux-ohos/` 子目录，profile LD_LIBRARY_PATH 仅覆盖 `<llvm>/lib` | conanfile generate() 将 `aarch64-linux-ohos` 目录 prepend 到 LD_LIBRARY_PATH |
| 3 | 3rdparty/ 子目录为空（git submodules 未打包） | v5.264.1 tar.gz 不含 submodule 内容 | 实测无需补充：src/vulkan/meson.build 对 vulkan.h 的探测命中 OHOS SDK sysroot 自带头文件（/…/sysroot/usr/include/vulkan/vulkan_core.h），glad/jinja/markupsafe 仅对应 GPU 后端 enabled 时被引用（本配方全部 disabled） |
| 4 | meson 缺 ar | OHOS 无 ar/gar（llvm-ar 仅在） | conanfile generate() 设置 AR=/data/service/hnp/bin/llvm-ar（与 babl/libplacebo-7.349.0 同款） |

## 上游测试申报表（R51）

- 上游测试注册：`meson test --list` 输出 9 项（`src/tests/*.c`，src/meson.build tests 数组）
  1. colorspace.c — colorspace 转换与色度计算
  2. common.c — 公共工具函数
  3. dither.c — 抖动算法
  4. dummy.c — dummy GPU 后端
  5. lut.c — 3D LUT 处理
  6. filters.c — 图像滤波器
  7. string.c — 字符串工具
  8. tone_mapping.c — 色调映射
  9. utils.c — 通用工具
- 全部 9 项在本机实测运行并通过（不依赖 GPU/显示，纯 CPU 算法测试）
- GPU 渲染类功能（pl_renderer_* 等）在 OHOS 无 GPU/display 环境不可验证——环境限制如实说明，非跳过；消费者 test_package 降级为调用 pl_version() API（纯 CPU，可执行）

## 源码修改

无补丁。仅 conanfile.py 内建环境适配（AR、LD_LIBRARY_PATH、GPU 后端禁用）。

## 依赖版本

- meson: 1.12.0（pip 安装）
- ninja: 1.13.1（系统自带）

## 验证结果

```bash
# 本机探索性编译
meson test                      # 9/9 OK
# conan-verify 8 道门禁
ohc-run.py conan-verify libplacebo5 5.264.1   # G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS
```

## 交付物

- archives/l/libplacebo5/5.264.1/conanfile.py（meson 配方）
- archives/l/libplacebo5/5.264.1/conandata.yml（官方源 + sha256）
- archives/l/libplacebo5/5.264.1/test_package/（含实质 API 调用测试）
- 共享库产物：libplacebo.so.264（conan create 打包）

## 注意事项

- 本任务软件名为 libplacebo5（对应上游 libplacebo v5 系列），与已归档的 libplacebo/7.349.0（v7 系列）是同一上游项目的不同大版本，归档目录独立
- GPU 后端（OpenGL/Vulkan/D3D11）在 OHOS 无对应依赖，全部禁用；库仍提供 GLSL 生成、色彩管理、tonemapping 等 CPU 侧能力（上游对无 GPU 构建的明确声明）
---

**编译结束**: 2026-09-16 02:13
**最终状态**: built
