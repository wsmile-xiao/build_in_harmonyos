# E321 - 修复 OHOS SDK lld 主机运行库时必须保持目标链接器语义

## 错误特征

初始故障与 E120/E132/E266 相同：CMake compiler probe 调用 OHOS SDK
`lld` 时，主机动态加载器找不到匹配的 `libxml2.so.16`，或者加载了 ABI 不匹配的
同名库，出现 `xmlFreeDoc: symbol not found`。

修复该故障后可能出现两种新的失败表面：

```text
Process not started
.../bin/absl_crc_memcpy_test
[permission denied]

0% tests passed, 241 tests failed out of 241
```

或者 CTest 将整套测试标记为 `BAD_COMMAND`，但此前 configure、compile、link
均已成功。

## 触发条件

- 构建系统：Conan 2 + CMake + OHOS SDK clang/lld。
- 阶段：修复 SDK `lld` 的主机 `libxml2.so.16` 依赖之后，执行目标测试之前。
- 条件一：用裸 `lld --version` 探测通用 driver，因未指定 flavor 而误判失败，
  随后注入 `-fuse-ld=/data/service/hnp/bin/ld`。
- 条件二：将 SDK `llvm/lib` 加入 `LD_LIBRARY_PATH` 的作用域同时覆盖
  `cmake.test()` / CTest。

## 根因分析

OHOS SDK 的 `lld` 是构建主机进程，它需要 SDK 自带的 ABI 匹配
`libxml2.so.16`。为它设置的 `LD_LIBRARY_PATH` 只属于 host-tool 环境，不能泄漏到
目标测试进程。

通用 `lld` driver 还需要通过程序名或 `-flavor` 选择具体后端。裸
`lld --version` 不是可靠的 ELF/GNU 后端健康检查；把该返回码直接解释为“SDK
linker 不可用”，会错误触发 GNU ld 回退。abseil 官方 CI #22206 证明这种回退
可以完成全部测试二进制的编译和链接，但 241 个目标均被 HarmonyOS 执行策略以
`permission denied` 拒绝。删除回退并使用 flavor-aware probe 后，CI #22584 和
#22968 均完整通过。

## 解决方案

### 推荐方案

1. 从 Conan 实际配置的 C/C++ compiler 执行 `-print-resource-dir`，动态推导当前
   SDK 的 `llvm/lib`，不要硬编码 SDK 版本目录。
2. 要求该目录存在 `libxml2.so.16`。
3. 仅在探测子进程中临时前置该目录，执行：

   ```sh
   LD_LIBRARY_PATH="$SDK_LLVM_LIB:${LD_LIBRARY_PATH:-}" \
     "${SDK_LLVM_LIB%/lib}/bin/lld" -flavor gnu --version
   ```

4. Conan 配方中仅让同一 host 环境覆盖 CMake configure/build/install。
5. 环境恢复后再运行 CTest；目标测试只继承其正常运行环境。
6. 如果匹配的 SDK 运行库不存在或 flavor-aware probe 失败，输出 probe stderr 并
   fail fast。

### 禁止做法

- 禁止把 `/data/service/hnp/bin/ld` 通过 `-fuse-ld` 或
  `CMAKE_*_LINKER_FLAGS` 静默注入为 fallback。该做法与 E266 当前推荐方案冲突，
  在需要执行目标 ELF 的 OHOS CI 中会产生“链接成功、运行被拒绝”的假成功。
- 禁止用覆盖 CTest 的大作用域 `LD_LIBRARY_PATH` 修复 host `lld`；SDK host 库会
  污染目标进程启动。
- 禁止硬编码 `ohos-sdk_X.Y.Z.W` 或 `lib/clang/15.0.4`。CI worker 的 SDK 位置和
  版本可能不同。

## 验证

abseil 20260526 在 PR #5118 上形成了完整对照：

| CI | 结果 | 证据 |
|----|------|------|
| #22036 | 失败 | `lld` 加载 `libxml2.so.16` / `xmlFreeDoc` 失败 |
| #22158 | 失败 | host `LD_LIBRARY_PATH` 泄漏，241 项 `BAD_COMMAND` |
| #22206 | 失败 | GNU ld 回退后，241 个 ELF 均 `[permission denied]` |
| #22584 | 通过 | flavor-aware SDK lld，无 fallback，L0/L1/test_package 通过 |
| #22968 | 通过 | 同一提交再次完整通过，排除单 worker 偶然性 |

复验命令：

```sh
CI_PACKAGES="archives/a/abseil/20260526" zsh ci/conan/build_and_test.sh
```

## 去重与关联条目

- `E120`、`E132`：解释 SDK `lld` 缺少 `libxml2.so.16` 运行库路径，本草稿复用其
  初始诊断，不重复创建该错误模式。
- `E266`：包含精确的 `libxml2.so.16` / `xmlFreeDoc` 指纹，但推荐 GNU ld 回退。
  本草稿记录该回退在目标 ELF 执行场景中的反例，并提供保持 SDK clang/lld 的方案。
- 本草稿新增的是“修复作用域和 linker 语义边界”，适用于其他在 OHOS CI 中既调用
  SDK host tool、又运行目标测试二进制的 CMake/Conan 配方。
