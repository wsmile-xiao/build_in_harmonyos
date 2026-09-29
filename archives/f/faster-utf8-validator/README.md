# faster-utf8-validator

非常快的 UTF-8 校验库（上游 AVX2/SSE4 SIMD 实现）。

## 软件信息

- 上游仓库：https://github.com/zwegner/faster-utf8-validator
- 版本：cf482014d0
- 许可：MIT

## 版本索引

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|----------|------|
| cf482014d0 | built | cmake | 首次 OHOS aarch64 适配：标量回退路径 |

## 适配说明

上游仅提供 x86 AVX2/SSE4 SIMD 实现（单文件 `z_validate.c`）。OHOS aarch64
平台无 AVX2/SSE4 指令，本适配在 `z_validate.c` 内新增标量回退实现
`z_validate_utf8`（相同的 UTF-8 验收语义），并通过补丁附带 CMakeLists.txt
构建入口与公共头文件 `z_validate.h`。x86 平台仍可定义 `AVX2`/`SSE4` 宏使用
SIMD 变体。

上游测试 `test.lua` 依赖 LuaJIT + x86 .so，aarch64 上无法直接运行；
46 项独立声明用例已移植为 C 测试目标（`test_upstream_port.c`）并全量通过，
详见版本目录 reports/。
