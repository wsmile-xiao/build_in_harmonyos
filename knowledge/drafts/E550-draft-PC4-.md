# E550 — 无条件 #pragma clang diagnostic ignored 引用 Clang≥16 才有的诊断组，Clang 15/-Werror 下编译失败

## 错误特征

上游测试/源码无条件写入新版本 Clang 才存在的诊断组忽略 pragma，在
Clang 15（OHOS 工具链）配合 `-Weverything -Werror` 编译时报：

```
test/test_shared.h:42:34: error: unknown warning group '-Wunsafe-buffer-usage',
                                                  ignored [-Werror,-Wunknown-warning-option]
#pragma clang diagnostic ignored "-Wunsafe-buffer-usage"
                                 ^
1 error generated.
```

## 触发条件

- 构建系统: cmake（上游测试 CMakeLists 带 `-Weverything -Werror`）
- 阶段: compilation（上游测试 / 构建目标编译任意一个翻译单元）
- 工具链: clang 15（OHOS aarch64 工具链）；诊断组 `-Wunsafe-buffer-usage` 为
  Clang ≥ 16 新增，低于 16 的 clang 不认识

## 根因分析

`#pragma clang diagnostic ignored "-Wxxx"` 中引用的诊断组若在当前编译器版本
不存在，clang 会把它当作 *unknown warning group*。配合 `-Werror` 时，
`-Wunknown-warning-option` 也被提升为错误，于是"本意是压制警告"的 pragma
反而变成硬编译错误。仓库内同类 pragma（如 `-Wglobal-constructors`、
`-Wunsafe-buffer-usage-in-libc-call`）已用 `__has_warning()` 条件守卫，唯独
`-Wunsafe-buffer-usage` 是无条件写入的。

## 解决方案

### 推荐方案（has-warning-guard）
用 `__has_warning()` 条件编译守卫包裹 pragma，与同文件既有模式保持一致：

```c
#if __has_warning("-Wunsafe-buffer-usage")
#pragma clang diagnostic ignored "-Wunsafe-buffer-usage"
#endif
```

低版本 Clang 下 `__has_warning()` 返回 0，整段被跳过；Clang ≥ 16 下正常生效。
该类修复必须作为 `patches/<NNNN>*.patch` 随配方登记（patch_type: portability），
并同步 `conandata.yml` 的 `patches:` 列表，保证上游测试在 OHOS 工具链上可复现
编译运行。

### 禁止做法
- ❌ 全局 `-Wno-unknown-warning-option` 压掉所有 unknown warning group（掩盖
  拼写错误等真实问题，且上游 `-Werror` 下还需要额外配 CFLAGS）
- ❌ 改上游 -Werror/-Weverything（改变上游测试语义，影响多编译器矩阵）

## 验证

```bash
# 上游测试编译 + 运行（修复后）
cmake -S . -B build -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang \
  -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
cmake --build build -j20 && cd build && ./json_test && ctest --output-on-failure
# 结果: json_test 1665/1665 通过, ctest 4/4 (json_test/address/undefined/thread) 通过

# 配方级验证
conan create archives/j/json.h/3.15 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 适用边界 / 反例

- 适用：上游无条件 `#pragma clang diagnostic ignored` 较新诊断组时，用
  `__has_warning()` 守卫；语义等价于编译器版本能力探测。
- 反例：若诊断组在目标工具链里确实存在且只是值不同（如 `-Wsign-compare`
  GNU/clang 都认识），不需要加守卫；若需要跨 MSVC/GCC，守卫块要放在
  `#if defined(__clang__)` 分支内。

## 关联条目

- 相关: E063（clang warnings + -Werror 的另类触发）、E197/E198/E199
  （clang 警告 → 源码补丁）、E321（header-only 配方）
- similar_to: E063