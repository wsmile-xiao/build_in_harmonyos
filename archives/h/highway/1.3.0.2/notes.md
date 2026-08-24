# Highway 1.3.0.2 verification notes

## Version bump reason

1.3.0.2 is a version bump from 1.3.0.1 to satisfy R37 (recipe revision collision
when manifest.yaml/notes.md are updated). No recipe or source changes.

## 2026-08-22 HarmonyOS aarch64 真机验证

### 验证环境
| 项目 | 值 |
|------|-----|
| 平台 | HarmonyOS (OHOS) 6.0, aarch64 |
| 编译器 | clang 15.0.4 (libc++) |
| Conan | 2.31.1 |
| CMake | 4.1.2 |
| Profile | ohos-local |

### 构建结果：✅ 通过

**产物清单：**
| 产物 | 数量 | 文件 |
|------|------|------|
| 静态库 | 2 | `libhwy.a`, `libhwy_test.a` |
| 头文件 | 40 | `hwy/*.h`, `hwy/ops/*.h`, `hwy/tests/*.h` |
| CMake 配置 | 3 | `hwy-config.cmake`, `hwy-config-version.cmake`, `hwy-config-release.cmake` |
| pkg-config | 2 | `libhwy.pc`, `libhwy-test.pc` |

### test_package 结果：✅ 通过

- NEON 路径自动选择 ✅ (`HWY_TARGET=536870912`)
- SIMD 向量运算正确 ✅ (`Lanes=2`, double 向量加法)
- 上游测试编译：60/60 通过（100%）

## Upstream test mode

The default package builds only the core library.
Set `-o highway/*:with_upstream_tests=True` to enable upstream tests via HWY_TEST_STANDALONE.
