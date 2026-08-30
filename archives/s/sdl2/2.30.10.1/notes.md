# sdl2 2.30.10.1 适配笔记（shared 版本）

## 说明
sdl2 2.30.10 已有 static 适配。2.30.10.1 是 shared 增强版本，
供 pygame 使用（pygame 的 C 扩展模块需要链接同一个 libSDL2.so 实例，
使 SDL 全局状态跨模块共享，否则 convert 等 API 因各模块独立 SDL 状态而失效）。

## 版本号策略（R37）
- 2.30.10：static binary（原有）
- 2.30.10.1：shared binary（本次新增，依赖 sdl2 shared 的下游使用）

## 修改
- conanfile.py generate()：shared=True 时 --enable-shared --disable-static
- test_package/conanfile.py test()：shared 运行时复制 .so 到 test 目录 + 设 LD_LIBRARY_PATH
  （OpenHarmony musl ld 不默认搜索可执行文件同目录的 .so，需显式 LD_LIBRARY_PATH）

## 构建
- autotools configure + make
- 默认 shared=False（static），shared=True 生成 libSDL2.so

## 验证
- conan create -o sdl2/*:shared=False：static 编译 + test 通过
- conan create -o sdl2/*:shared=True：shared 编译 + test 通过（libSDL2.so 生成）
- 测试：test_SDL2（version 检查）
---

**编译结束**: 2026-08-27 11:33
**最终状态**: built
