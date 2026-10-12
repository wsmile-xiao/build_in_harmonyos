## PR 信息

- **三方库名称**：redex
- **上游版本**：2026.04.30
- **上游仓库地址**：https://github.com/facebook/redex
- **适配路径**：路径 A（基础适配）+ 路径 B（知识贡献）；HD1–HD4 逐项重判均未命中，不申请路径 C
- **使用知识库**：E2026100905-draft-redex-r219；预生成 ZIP/DEX 内部完整性与构建消费者的模式、哈希、工作目录绑定

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 149 | Automake 单元 GTest wrapper；每个 wrapper 的叶子清单单独盘点 |
| 集成测试 | 25 | Automake 集成 GTest wrapper |
| 其他测试 | 1 | 原始 `test/check_num_passes.sh` |
| **合计** | **175** | 174 个 GTest wrapper + 1 个 Shell 独立入口；GTest 另计 2009 个叶子，不把 wrapper 当叶子 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 149 | 不变 | 完整执行原 GTest wrapper 及其叶子 |
| 集成测试 | 28 | 原 25 + Shell 1 + 新增 2 | Shell 在此行汇总但不重复计数；新增安装包消费者及独立实际 APK 转换各 1 项 |
| 鸿蒙特有测试 | 1 | 新增 | 真实 OHOS/arm64 HMDFS 安装路径下已签名 ELF 的执行及前后哈希检查 |
| **合计** | **178** | **+3** | 原生上游 175 + 普通包消费者 1 + 鸿蒙专项 1 + 独立 APK 消费者 1；重复构建模式不重复计数 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

- `test/unit/ConfigFilesTest.cpp`：临时文件优先使用任务 `TMPDIR`，未设置时保留原 `/tmp` 回退，保留原 9 个叶子和断言。
- `test/unit/constant-propagation/BoxedBooleanPropagationTest.cpp`：修正 fixture 类型描述符；保留 TRUE/FALSE 的区分断言，不以放宽预期遮盖失败。
- `test/unit/StringTreeTest.cpp`：经 `unsigned char` 格式化编码字节，移除目标 plain-char 符号性对输出的影响。
- `test/samples/Makefile.inc`、两个 sample 的 `Makefile.am` 及 `configure.ac`：显式哈希绑定 prebuilt APK 模式，绕开目标不能执行的 host aapt2；默认模式不变，所有消费者和测试分母保留。目标 JDK 真实生成其余 Java fixture。
- Autotools 检测/构建入口保留 C++ 标准和实际检测的 Bash。产品侧输出排序、字符串视图生命周期和 boxed-Boolean 描述符修复分别保留在 18 项补丁中。

完整通过证据属于 r376；历史 r372 的单叶失败未被后续通过反向解释为已证明精确根因。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增安装包消费者、鸿蒙专项与独立实际 APK 转换验证包的可消费性，不替代上游测试。
`test_package/test_redex_package.py` 调用同包 `redex-all`/Python 驱动；
`test_package/harmony_tests/test_signed_hmdfs.py` 校验实际 OHOS、AArch64 ELF、
HMDFS 路径、非空 `.codesign`、真实 pass discovery 及执行前后哈希。
独立 APK 事务调用安装后的驱动/二进制、默认配置、android.jar 和保守 keep-all
规则，校验真实输出 ZIP/DEX、统计及完成日志；该事务不会再次运行 175 项上游。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：175/175（100%）
- 新增测试用例通过率：3/3（100%）

- 原生 r376：174/174 wrapper、2009/2009 GTest 叶子、Shell 1/1、receipt 10/10；原冻结控制器 release/postrelease 2/2。结果归档 SHA-256 `69a5ec823bcdb096bd9e79c98ff56ccae76a06c184da56eaaaed4f5a3892fec2`。
- 官方 official-finish-r001：真实 Conan/create、官方 W3 子步骤和 Harmony 1/1 通过；原 `.ci-result.json` exit0，SHA-256 `32c88ea52dad327b39d8e33a47cc9e4d57fd235ff81daf85ce464b720b1f45f7`。整体 finish 保留 RC1/失败，后置失败集仅 step5b/step8；不将总失败改成成功。L2/L4/L5 的原 skip 不算已执行。
- APK r003：唯一转换 RC0/无超时、21 项实际 pass 统计、ZIP CRC/DEX SHA-1/Adler-32 与输入/产品前后哈希通过，release/postrelease 2/2。归档 SHA-256 `61a195657f19bc007d2457a74e0d95f3e6d36ce5c8bc716f8476dd79f60523ae`。仅证明 conservative keep-all 下未签名转换，不证明签名、对齐、Android 安装/运行、语义等价或缩小率。
- 三项事务分别绑定各自 tree、依赖 revision、run/boot/root 与归档，不拼接成一个事务。产品 recipe/patch 没有因报告、知识或私有流程修复而修改。
- 完整命令、测试快照与限制见 `reports/test-report.md`；本地证据不冒充当前 PR HEAD 的平台 Review、CI 或提审回读。

---

## 补充说明

- 关联 Issue：#1092
- 队伍名称：天天开心
- 申请人显示标识：2301_80739235
- 源分支：OpenHarmonyPCDeveloper:feat/redex-2026.04.30
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 知识增量：同 stem KV/MD 区分传输字节、ZIP/DEX 内部完整性和实际消费者绑定；增加原生完整执行与真实转换的独立证据及不适用边界。不把既有全局知识说成空白，不以修复轮次或测试数量申报高难。
- 提交流程只在当前 HEAD 的 PRE_CREATE、POST_CREATE、平台最新 AI Review 和平台 CI 满足后推进提审；不上传制品、不 force push。共享框架未修改，私有 submit 仅含用户授权的废弃 packaging 检查兼容修正，兼容 fixture 不代替生产合同。
