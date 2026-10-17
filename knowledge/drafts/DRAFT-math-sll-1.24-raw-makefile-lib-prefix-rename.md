# DRAFT-math-sll-1.24-raw-makefile-lib-prefix-rename

> 草稿（Path B 知识库扩展候选），由 math-sll 1.24 适配中 test_package
> `find_package` 找不到无 lib 前缀静态库的真实失败与已验证修复产生。
> 本文与同名 `.kv` 配对，逐字段一致。仅为本地知识草稿。

## topic

上游裸 Makefile 静态库产物归档无 lib 前缀（`math-sll.a`），CMakeDeps 按惯例查找 `lib<name>.a` 失败，package() 需 `os.rename` 重命名

## error_signature

`conan create` test_package 阶段 `find_package(<pkg>)` 报
`Library '<lib>' not found in package. If '<lib>' is a system library, declare it with 'cpp_info.system_libs'`，
同时主包日志显示静态库已成功构建并复制进 package（文件名如 `math-sll.a`，无 `lib` 前缀）。
CMakeDeps 按 Linux/OHOS 惯例拼出 `lib<name>.a` 查找，找不到库文件。

## root_cause

上游裸 Makefile 项目把产物直接命名为 `<name>.a`（如 `math-sll.a`）而非
`lib<name>.a`。conan `package()` 用 `copy(pattern='*.a')` 原样复制后包内只有
`math-sll.a`。Conan CMakeDeps 生成 target 时按 `cpp_info.libs=['math-sll']`
拼 `libmath-sll.a` 查找，导致 `find_package` 报 Library not found。错误在
消费侧 test_package 才暴露，主包编译与打包本身都成功——属于典型的
"包装进包了但命名不符合约定"陷阱，而非"产物未复制"陷阱。

## durable_solution

1. `package()` 复制后显式
   `os.rename(os.path.join(package_folder, 'lib', '<name>.a'),
             os.path.join(package_folder, 'lib', 'lib<name>.a'))`，
   满足 CMakeDeps 命名约定。
2. conan `copy()` 不支持在目标路径直接改文件名（目标按目录语义处理），
   必须先 copy 到 lib/ 再 `os.rename`。
3. 复跑 `conan-verify` 确认 G2（test_package）通过；消费者断言对迭代近似
   运算（`slldiv`=x*`sllinv`(y) 倒数、`sllsqrt`、三角函数）用 1e-6 容差，
   避免把算法舍入误判为适配失败。

## impact

任何上游裸 Makefile 输出非 `lib<name>.a` 命名归档的静态库配方都会遇到
"主包编译打包成功但 test_package find_package 找不到库"的同类失败；
`os.rename` 重命名模式可跨库复用。边界：产物已复制但命名不符合 `lib<name>`
约定（区别于 embedded-cli 草稿"产物在 build 子目录未复制"的边界）。

## evidence_references

- math-sll 1.24 `conan-verify` 报告：G2 修复后 PASS，test_package 9/9 断言通过
- `conan-create.log` 首错：`Library 'math-sll' not found in package`（修复前）；修复后 G2 PASS
- `test_ohos/run_ohos_test.sh` T1/T2/T3 ALL PASS（aarch64 归档 / 无宿主路径泄漏 / 消费者运行）

## recovery_condition

不适用（适配配方修复，无恢复动作）；后续同类库按上述 `package()` `os.rename` 模式处理即可。

## status

draft_pending_review

## similar_to

`DRAFT-embedded-cli-0.1.4-cmake-subdir-static-lib-package`（同报错串、静态库场景，但根因为 add_subdirectory 产物漏复制，机制不同，非 causal_duplicate）
