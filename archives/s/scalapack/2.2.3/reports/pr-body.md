## PR 信息

- **三方库名称**：ScaLAPACK
- **上游版本**：2.2.3
- **上游仓库地址**：https://github.com/Reference-ScaLAPACK/scalapack
- **适配路径**：路径 A（基础适配） / 路径 B（贡献创新） / 路径 C（高难度挑战）
- **使用知识库**：`fortran-mpi-provider-abi-gate`、E221、`E2156-draft-2301`、`E2155-draft-2301`

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 无独立上游单元测试；所有注册入口均通过 MPI 启动并验证多进程组件协作 |
| 集成测试 | 100 | CTest：BLACS 2、PBLAS 24、传统 LIN/EIG 74 |
| 其他测试 | 0 | 没有 CTest 清单之外的独立上游入口 |
| **合计** | **100** | `CMake.test(build_tool_args=["-j1"])` 实际展开为 `cmake --build <build_folder> --target test -- -j1 -j1`，注册清单与执行终态均为 100 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 0 | 不变 | 无独立单元测试；未把断言数重复计为独立用例 |
| 集成测试 | 101 | +1 | 保留上游 100 个 MPI CTest，并新增 1 个 CMakeDeps/BLACS/`numroc_` 两 rank 消费者 |
| 鸿蒙特有测试 | 0 | 不变 | 无独立鸿蒙特有测试；ELF 签名和目标运行是同一消费者流程的执行门禁，不另计独立测试 |
| **合计** | **101** | **+1** | 上游 100 个入口加 1 个独立消费者 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

1. **修改的测试文件**：`BLACS/TESTING/blacstest.f`
   - **修改原因**：程序写出 `DONE BLACS_GRIDEXIT` 后进入预期的 `MPI_Abort`，Flang 缓冲可能在 abort 前丢失最后一行，导致外层 CTest 误判。
   - **修改内容**：在完成标记后立即执行 `FLUSH(OUTNUM)`，不改变 abort 与退出语义。
2. **修改的测试文件**：`BLACS/TESTING/runtest.cmake`
   - **修改原因**：复制 ELF 会破坏 `$ORIGIN` 相对 RUNPATH；未引用的空 `TESTSTRING` 会令 `list(APPEND)` 参数数不足。
   - **修改内容**：从原 `RUNTIMEDIR` 执行测试程序，不再复制到输出目录，并把 `${TESTSTRING}` 作为一个引用参数追加。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游已有完整 100 项 MPI CTest 清单。新增的 `test_package/test_scalapack.c` 是包消费契约测试，不用于替代任何上游入口；它通过生成的 `scalapack::scalapack` target 验证两 rank BLACS grid 和 LP64 `numroc_` 分布结果。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：100/100（100%）
- 新增测试用例通过率：1/1（100%）
- W3 输入：22311 bytes，SHA-256 `2c51a5d00154b616ae98c6b5bcce9eb857ef6378899905d0ea300efc4360d9e5`
- W3 终态：RC 0，`2026-08-19T06:20:44Z` 至 `2026-08-19T07:55:58Z`
- 上游原始日志：100 个 PASS 行、唯一 `100% tests passed, 0 tests failed out of 100` 总计；`LastTest.log` SHA-256 `64d7de3901c80decadaa30259d598930c04fd9558a1098714a76138db3794fe0`
- BLACS：`xCbtest` 与 `xFbtest` 均通过且各包含一次 `DONE BLACS_GRIDEXIT`
- Conan 包：`scalapack/2.2.3#4cac783ec3f21720e060656fd16f310e:54349a6384308b1ece84295080a8d7090b4bb232#9e704819ec10677dc1a8636a89cc817c`
- 消费者：打包的 `mpiexec -n 2` 下 rank 0/1 均报告 `failures=0`
- 聚合证据：7432321 bytes，SHA-256 `ba563a6cf5a860577d3cc6caad8a69078bf7d211389ca2d53ccfc380e26851d1`；独立校验 18 个安全成员、16/16 payload 哈希、100 个 CTest PASS 行、2/2 BLACS marker 和 2/2 rank 输出

---

## 补充说明

- 关联 Issue：#1647
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：2301_80739235:feat/scalapack-2.2.3
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：依赖固定为 `openblas/0.3.34`、`mpich/5.0.1.2` 和 `flang-ohos/20.1.0`；本 PR 仅提供 shared 版本，直到 Flang runtime 能作为 host-visible 链接依赖传播给静态消费者。知识查重确认 E221/E216/E217 仅为相邻模式，本 PR 新增 E2156/E2155 配对草稿并保留明确适用边界。
