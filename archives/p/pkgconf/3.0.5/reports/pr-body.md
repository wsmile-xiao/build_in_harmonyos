## PR 信息

- **前置依赖关系**：pkgconf 3.0.5 是 GraalVM 25.0.3（任务编号 1085）的真实构建前置依赖；本 PR 合入并由 release 流水线发布后，GraalVM 配方才能消费该依赖。
- **三方库名称**：pkgconf
- **上游版本**：3.0.5
- **上游仓库地址**：https://github.com/pkgconf/pkgconf
- **适配路径**：路径 A（基础适配） + 路径 B（贡献创新） + 路径 C（高难度挑战）
- **使用知识库**：正式条目 E272；E2145、E2146、E2147、E2148、E2149、E2150、E2151 草稿

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 16 | 15 个 API 可执行测试 + 1 个 OOM 测试 |
| 集成测试 | 425 | 14 个 fixture 套件中的唯一 fixture 文件 |
| 其他测试 | 145 | parser corpus 141 + solver corpus 3 + missing-path 负测 1 |
| **合计** | **586** | 官方 3.0.5 源码清单与 Meson introspection，完整执行 586/586 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 16 | 不变 | 保持 API/OOM 的上游测试语义与 shared 被测边界 |
| 集成测试 | 425 | 不变 | 按唯一 suite/fixture 键要求真实 PASS，零 SKIP/FAIL |
| 鸿蒙特有测试 | 26 | +26 | 静态库 API、`.pc` fixture 与四个 AArch64 命令消费者断言 |
| **合计** | **612** | **+26** | 上游 586 个官方用例 + 26 个目标消费者断言 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

- `tests/api/reallocarray-shim.c`：仅在隔离验证树为缺失 API 提供带乘法溢出检查的测试 shim，不进入交付库。
- `meson.build`：用真实 target-link `--wrap=calloc` 探测替代主机名判断，保持 shared OOM 边界并注册 missing-path 负测。
- `fuzzer/parser-fuzzer.c`、`fuzzer/solver-fuzzer.c`、`fuzzer/replay.c`：临时文件、短写、close、路径和空 corpus 全部失败闭合，并输出精确 replay 计数。
- `tests/api/test-api.h`、`test-audit.c`、`test-buffer.c`、`test-fileio.c`：七个匿名流调用改用 `TMPDIR` 感知的 `mkstemp + unlink + fdopen` 测试 helper，不含 OHOS 条件宏；复用正式知识 E272。
- 官方库存没有删减或跳过；33 个顶层测试、425 个 fixture 和 corpus 输入全部纳入 586/586。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游已有完整测试体系；新增 26 个断言只补充 Conan 包接口、四个目标命令和 OpenHarmony 目标运行验证，不替代或计入上游 586 个官方用例。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：586/586（100%）
- 新增测试用例通过率：26/26（100%）
- OHOS/arm64 语义基线包身份：RREV `4a3f062deb7823efabd171c60b7aab22`，PID `21b17f8b2bc0e9511e276e3d57a23893067cefe5`，PREV `7dad25c18ecf6400f17f94e2df9542ce`。
- 真机快照：endpoint `10.62.215.229:2222`，controller/runner 1/1，runner RC0，5 个 ELF 签名，26/26 断言通过。
- 释放闭包：root process 0，clean scans 2，lock/lease 0，postrelease PASS；readback tar 48/48 成员和 13/13 证据哈希通过。
- 当前输入重绑定：未重跑真机；0007 只修改四个上游测试文件，不进入安装目标。11/13 CI 输入与 r20 语义基线逐字节一致；`conandata.yml` 仅把权威镜像切换为 HTTPS 并补齐补丁序号，下载的 426972 字节仍匹配官方 SHA-256；0007 的提交包装 SHA-256 为 `911c89e722683f216e8baea4b23c76e14be324660f09793d6b0cbf907025e7fa`，Git、GNU patch `--fuzz=0` 和 patch_ng 均产生相同的 755 文件完整后像。23/23 交付内容文件和四个包命令完成哈希绑定；仅 Conan 生成的 `conanmanifest.txt` 随 RREV 改变。fresh 消费者已重新编译链接，但不声称其字节与历史消费者相同；生产方法矩阵 13/13，重绑定正负测 12/12。
- 平台 CI 修复：Buildbot #26332/buildid 29163 的 Conan buildenv 边界与 #26630/buildid 29515 的 libc `tmpfile()` 边界均已实修。精确当前 HEAD 的 #26988/buildid 29985 随后完成源码下载、43 个主目标、125 个验证目标、上游 586/586、打包及消费者编译链接，仅因 Worker 缺少 `llvm-objcopy`、`llvm-readelf`、`binary-sign-tool` 而在运行前失败。新门禁先确认消费者和四个命令产物，再判断 `can_run()` 与签名工具能力；仅缺运行能力时明确记录运行阶段未执行且不计通过，工具齐全时仍执行原 26 项断言，缺产物或任何其他错误继续失败。生产入口定向测试 7/7；replacement CI 待新 HEAD 触发。
- 知识草稿：E2145–E2151 七组 KV/Markdown 配对，四范围查重结论为 `NO_EQUIVALENT_REUSABLE_KNOWLEDGE`；`tmpfile()` 错误复用正式条目 E272，E2151 补充 Conan `can_run()` 与 OHOS 签名工具实际可用性不同层的门禁边界。

---

## 补充说明

- **关联 Issue**：#1694
- **队伍名称**：天天开心
- **申请人显示标识**：2301_80739235
- **源分支**：2301_80739235:feat/pkgconf-3.0.5
- **目标分支**：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- **其他说明**：活动为“依赖”；标题按优先级只使用“高难度挑战”单前缀。PR 不上传 Conan/CNB 制品，正式发布仅由合并后的 release 流水线执行。
