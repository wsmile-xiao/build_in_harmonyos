# nanosvg 0.0-git.239e102 适配笔记

## 编译环境
- 构建系统: cmake（直用上游自带 CMakeLists.txt，零补丁）
- 编译日期: 2026-10-04
- 编译器: clang 15（aarch64-linux-ohos 目标，OHOS aarch64 profile）
- 状态: built

## 上游形态

- 仓库: https://github.com/memononen/nanosvg（master-only，无 tag 无 release）
- 版本号规则: 0.0-git.{master HEAD hash 前 7 位} → 本版本 = master @ 239e102ec2c691f2902e20ace2ed36ee4a35cfe6
- 源码包: 官方 GitHub master 分支 tarball（R39 官方源；ghfast.top 镜像在前加速，
  两源实测逐字节一致），sha256 实测:
  d987edb199754732eb3a3142546cf3634962294f26cd247b71ed7f580428458b
  （git ls-remote 核验 master HEAD = 239e102e…，与版本号一致，无漂移）
- 许可证: Zlib（LICENSE.txt，Copyright (c) 2013-14 Mikko Mononen）
- 交付形态: header-only 双库 —— nanosvg.h(88,980B 解析器) +
  nanosvgrast.h(39,398B 光栅化器)，各自 NANOSVG_IMPLEMENTATION /
  NANOSVGRAST_IMPLEMENTATION 宏激活实现段
- 上游构建: 自带 CMakeLists.txt（双静态库 + install/export），另有 premake4.lua（历史遗留）

## 编译步骤

1. conan create -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=…（CI 同款命令）
2. source(): conandata URL 列表下载解压（strip_root）——镜像优先、官方兜底
3. build(): cmake configure + build（上游 CMakeLists 原样：configure_file 生成
   实现单 TU → libnanosvg.a + libnanosvgrast.a）
4. package(): cmake install（include/nanosvg/ 双头 + lib/cmake/NanoSVG export）
5. test_package 阶段: 消费者断言套件真跑（ctest + 直跑双通道）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 双 header-only 库如何打包 | nanosvg.h/nanosvgrast.h 各自独立 *_IMPLEMENTATION 宏，单库打包会让光栅化器消费者背上解析器 | 直用上游 CMakeLists 双库方案：libnanosvg.a + libnanosvgrast.a，package_info() components 双组件映射上游 export（nanosvgrast requires nanosvg，与上游 target_link_libraries 对齐） |
| 2 | conandata 镜像预置是否违规 | CI worker 网络对 GitHub 直连不稳定 | conandata URL 列表（ghfast.top 镜像在前 + 官方兜底），两源 sha256 实测逐字节一致——libshumate 1.7.0 已合入先例同款列表格式 |
| 3 | 无宽高属性 SVG 的尺寸断言 | <svg><path .../></svg> 无 width/height/viewBox 时 image->width/height 由 shape bounds 自动推导 | 断言锚定 path->bounds [0,0,10,10] + 推导出的 image 10x10（行为经实测确认：scaleToViewbox 的 nsvg__imageBounds 回退路径） |
| 4 | 默认填充色锚定 | path 无 fill 属性时 SVG 规范默认黑色 | 实测确认 NSVG_PAINT_COLOR + 0xff000000（不透明黑，ABGR 序），光栅化中心像素 (0,0,0,255) 断言与之闭环 |

## 源码修改

无补丁（patches: {}）。上游 nanosvg.h / nanosvgrast.h / CMakeLists.txt 零修改，
本地探针程序（~/huawei/tmp/nanosvg-dl/probe*.c）仅为断言锚点校准，不入包。

## 依赖版本

W0 依赖审计: 零第三方依赖。
- nanosvg.h: C99 纯算法（stdio 仅 nsvgParseFromFile 路径），无系统头以外的依赖
- nanosvgrast.h: 纯算法，无系统头
- 上游 CMake: find_library(m) 可选链接 libm（musl/OHOS 折叠进 libc，-lm 无害）

## 验证结果

```bash
# 本机原生探针（clang -O1，与 OHOS 目标同一上游快照）:
#   解析: 1 shape / 1 path / npts=13 / closed / bounds=[0,0,10,10]
#         fill=0xff000000 stroke=NONE image=10x10（bounds 自动推导）
#   光栅化 scale=1: 100/100 像素覆盖(alpha>=128)，中心 (0,0,0,255)
#   光栅化 scale=2: 400/400 像素覆盖，18x18 内部 324/324 全覆盖
#   stroke SVG: stroke=0xff0000ff(#ff0000) fill=NONE line→npts=4
# conan create test_package 阶段: 33 条消费者断言全过（见 test_package/MANIFEST.yml）
```

## 注意事项

- 消费者链接 libnanosvg.a / libnanosvgrast.a 时不要定义 *_IMPLEMENTATION 宏（符号已在库内）
- 光栅化器消费者同时需要解析器：cpp_info.components 已声明 nanosvgrast → nanosvg 依赖
- 上游 master 分支无版本 tag：引用本包固定用 nanosvg/0.0-git.239e102，
  后续上游演进需按 0.0-git.{新 hash7} 递增新版本目录
- 上游 README 声明 "not actively maintained"，锁定快照 hash 即锁定行为
