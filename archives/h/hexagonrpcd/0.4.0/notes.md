# hexagonrpcd 0.4.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-02
- 编译器: clang 15 (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. `ohc-run.py init-build hexagonrpcd 0.4.0 --url=https://github.com/linux-msm/hexagonrpc/archive/refs/tags/v0.4.0.tar.gz`
2. 编写 conanfile.py（meson 配方）：MesonToolchain 生成 + `_inject_ar_ranlib()` 注入 llvm-ar/llvm-ranlib
3. `conan create . --build=missing -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
4. conan create 通过，test_package 运行成功（fastrpc context API OK）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson configure 报 "Unknown linker(s): llvm-ar-15/llvm-ar/ar/gar" | OHOS 工具链无裸 ar/ranlib，profile 仅声明 c/cpp | `_inject_ar_ranlib()` 将 llvm-ar/llvm-ranlib 注入 conan_meson_native.ini |
| 2 | `meson_layout` / `meson.compile()` 导入失败 | OHOS 适配版 conan 2.29.1 API 差异 | 改用 `basic_layout` + `meson.build()`（与 aravis 同款） |
| 3 | test_package 找不到 `libhexagonrpc/fastrpc.h` | 上游 meson.build 未 install_headers；package_type=application 时 CMakeDeps 不导出 include 目录 | package() 手动拷贝 include/；package_type 改 library + 显式声明 includedirs/libdirs/bindirs |

## 源码修改

无补丁（上游源码零修改，全部适配在 conanfile.py 配方层完成）。

## 依赖版本

- 无外部硬依赖（json-c 为可选依赖，缺失时跳过 sscregistrygen 工具）
- 构建工具: meson 1.11.1 / ninja 1.13.1 / conan 2.29.1

## 验证结果

```bash
conan create . --build=missing -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# 输出: hexagonrpcd/0.4.0: Package created
# build() 内嵌上游 meson test（2/2 通过）:
#   1/2 fastrpc:iobuffer  OK
#   2/2 fastrpc:hexagonfs OK
# test_package: hexagonrpcd: fastrpc context API OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/hexagonrpcd | FastRPC 守护进程 |
| bin/hexagonrpc/chrecd | CHRE 守护进程 |
| lib/libhexagonrpc.so.0.4 | FastRPC 共享库（soversion 0.4） |
| include/libhexagonrpc/*.h | 公开头文件（fastrpc.h/interface.h/session.h） |

## 注意事项

- 上游 `meson test`（iobuffer/hexagonfs）运行时依赖 /dev/fastrpc 设备节点，HarmonyOS PC 无该设备，仅编译验证（同上游 CI 行为）。
- 产物含可执行文件，已按 R38 创建软件级 commands.json（type=tool, binary=false，未发布前不虚标）。
---

**编译结束**: 2026-08-02 16:13
**最终状态**: built
