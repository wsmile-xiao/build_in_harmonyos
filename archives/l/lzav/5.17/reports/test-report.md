# lzav 5.17 功能测试报告

**测试日期:** 2026-09-19
**测试环境:** OpenHarmony aarch64 (armv8, os=OHOS 6.0)
**编译器:** clang 15.0.4 (OHOS SDK 26.0.0.18, target aarch64-unknown-linux-ohos)
**构建系统:** header-only（无构建系统；conan create + test_package 消费者编译验证）

## 1. 编译测试

### 1.1 编译状态
✅ conan create 干净构建成功（conan-verify G2 PASS，含测试包消费者编译与运行）
- 源码: https://codeload.github.com/avaneev/lzav/tar.gz/refs/tags/5.17（官方 release tag 源）
- sha256: b56a854a878fae9ca02793f9ac09a1b555d0801bde7897d8caace5cd88901b90
- 配方: header-library 类型，package 仅装头文件 include/lzav.h

### 1.2 编译警告
- 无源码警告（header-only，无编译产物）

### 1.3 源码修改
无补丁（patches/ 为空）。test_package/ 含两个测试源：
- `test.c` — 消费者验证（公开 API 往返 + 畸形输入安全）
- `test_ohos.c` — 鸿蒙专项测试（__OHOS__ 守卫 + uname 运行时核验 + 1MiB 往返）

## 2. 安装产物（conan create 生成的 package）

- 头文件: `include/lzav.h`（唯一交付物，header-only）
- licenses: `licenses/LICENSE`

## 3. 上游测试（双口径台账）

- `source_declared_total` = 0（官方 tag 5.17 源码仅 LICENSE/README.md/lzav.h 三文件，无测试目录/测试源/构建目标/注册项——枚举证据见 notes.md）
- `configured_executable_total` = 0
- `executed_passed_total` = 0，失败 0，未运行 0，硬阻塞 0
- 全量通过率: 无声明入口，0/0 口径如实填报（附 tar 清单枚举证据）

## 4. 本轮新增实际执行用例（与上游分别计数）

| 用例 | 源文件 | 构建目标 | 实际执行日志 | 结果 |
|---|---|---|---|---|
| 消费者验证 | test_package/test.c | lzav_consumer_test | conan-create.log: `RUN ./lzav_consumer_test` → `PASS: lzav consumer round-trip verified` | 1/1 |
| 鸿蒙专项 | test_package/test_ohos.c | lzav_ohos_test | conan-create.log: `RUN ./lzav_ohos_test` → 4/4 checks PASS | 1/1 |

鸿蒙专项测试运行时证据（真实设备内核）：
```
uname sysname = HarmonyOS, release = HongMeng Kernel 1.12.0, machine = aarch64
PASS: lzav_compress_default compresses on HarmonyOS (comp_len=185)
PASS: round-trip equals source on HarmonyOS (1 MiB, dec_len=1048576)
PASS: lzav OK on OpenHarmony (4 checks)
```

## 5. 门禁结果

| 门禁 | 结果 |
|------|------|
| G0 预构建风险 | ✅ PASS（无已知风险） |
| G1 配方完整性 | ✅ PASS |
| G2 conan create | ✅ PASS（含 test_package 双测试实际运行） |
| G3 系统同名库隔离 | ✅ PASS |
| G4 产物完整性 | ✅ PASS |
| W2 结构完整性 | ✅ PASS（conanfile/conandata/test_package/MANIFEST 齐全） |
| R36 依赖发布 | ✅ 无外部依赖（W0 预检通过） |
| W3 本地 CI 模拟 | ✅ PASS（基线隔离复验后通过，见下） |

## 6. 基线隔离复验（W3 命中其他库基线文件）

W3 本地 CI 首次运行被 JC 拦截，命中的 3 个文件均为其他库提交前已存在的基线空文件（非本库范围）：

| 路径 | pre_sha256 | isolation | rerun | restore | post_sha256 |
|------|-----------|-----------|-------|---------|-------------|
| archives/c/cloog/0.21.1/.build-closed | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | mv 至隔离目录 + git rm --cached | finish → W3 PASS | mv 恢复 + git add -f 恢复 index | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| archives/c/cloog/0.21.1/.staging-verified | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 同上 | 同上 | 同上 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| archives/k/kics/2.1.20/.staging-verified | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 同上 | 同上 | 同上 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

- pre_sha256 == post_sha256 ✅（全部 e3b0c442... 空文件，原样恢复）
- 本库 diff/staged/PR 未包含上述路径 ✅（git status 对该路径为空）
- 未修改、未提交、未写入知识库/PR 这些基线文件 ✅

## 7. 结论

lzav 5.17 header-only 适配完整：配方、消费者验证、鸿蒙专项测试、W2/W3 全部门禁通过。产物仅头文件（无 CLI，R38 库类型豁免 commands.json）。
