# mimalloc 3.2.8 适配笔记

## 适配日期
2026-07-16

## 适配环境
- 平台: OHOS aarch64
- 编译器: clang 15
- Conan: 2.x

## 构建说明
使用 CMake 构建。
- **必须** `MI_OVERRIDE=OFF` — mimalloc 默认会尝试覆盖系统 malloc/free，但在 OHOS 上会导致段错误 (SIGKILL)
- `MI_SECURE=ON` — 启用安全模式，生成 `libmimalloc-secure`
- `MI_LIBC_MUSL=ON` — 鸿蒙使用 musl libc，需要启用相关兼容选项

## 测试说明
test_package 调用 mi_malloc/mi_free 验证基本功能。上游测试 (test-api, test-stress 等) 通过 MI_BUILD_TESTS=ON 启用。

## 已知问题
- 禁止启用 MI_OVERRIDE，否则运行时会段错误
- 不支持通过 LD_PRELOAD 方式全局替换 malloc

**最终状态**: built
