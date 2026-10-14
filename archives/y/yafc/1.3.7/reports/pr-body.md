## PR 信息

- **三方库名称**：yafc
- **上游版本**：1.3.7
- **上游仓库地址**：https://github.com/sebastinas/yafc
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：E338、E272（passwd/tempfile 运行限制）；本 PR 的 E12242-draft-2501 存在性宏观察器草稿及同 stem MD

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
| --- | ---: | --- |
| 单元测试 | 0 | 完整官方发行包未注册 TESTS/check_PROGRAMS/check_SCRIPTS |
| 集成测试 | 0 | 完整 Makefile.am/configure.ac 盘点无注册集成测试 |
| 其他测试 | 0 | make check 实际执行，无注册测试；构建探测不充作上游用例 |
| **合计** | **0** | 官方源 SHA256 4b3ebf62423f21bdaa2449b66d15e8d0bb04215472cb63a31d473c3c3912c1e0；完整盘点见提交证据 upstream-inventory.txt |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
| --- | ---: | --- | --- |
| 单元测试 | 0 | 不变 | 没有虚构上游用例 |
| 集成测试 | 4 | +4 | FTP 登录/list、二进制下载、二进制上传、远端删除 |
| 鸿蒙特有测试 | 2 | +2 | 安装包版本与帮助启动；验证缺 passwd 条目环境下真实执行 |
| **合计** | **6** | **+6** | test_package/test.py；全部为新增安装消费者，不计入上游分母 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游无注册测试，原始 make check 保留并实际执行；没有删测试、减少上游分母或用新消费者冒充上游测试。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增 test_package/conanfile.py、test_package/test.py、test_package/MANIFEST.yml。
消费者必须运行安装包 bin/yafc；回环 FTP fixture 只监听 127.0.0.1 随机端口。
上传/下载分别核对完整 65792 字节，服务端保存实际上传数据后核对；删除验证 DELE 和状态。
临时凭据及文件仅用于本任务 fixture，不改用户 SSH 服务、密钥或系统路径。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用）
- 新增测试用例通过率：6/6（100%）

当前配方通过 OHOS arm64 原生 ConanVerifier、官方 finish 的 W3 本地 CI 子步骤和独立真机事务。
run_id：yafc-full-finish-r2-20261011T104500Z；endpoint：10.62.201.39:2222；
boot_id：c54c7831-20b9-452b-ada4-c221a56df139；UID：20020084。
日志 SHA256：22b32ac8ccc13019be073387d072e3c1da048f80acb7a47b396356a67b60230c。
生产 ELF SHA256：67581271002e6da0015bf590dc881b76917c53e554814212d78c536447eae869。
12 回执完整，launch_count=1，release/postrelease PASS。
完整 finish 保留 RC1/PARTIAL_POST_W3：step5b/step8 的旧全局知识字段与 staging/knowledge-done 检查失败；
正式 Conan 与官方 W3 子步骤分别通过，不称整个 finish PASS。
ConanVerifier L2/L4/L5 因 cache ID 查找 SKIP，不冒充执行；安装消费者有真实六项 PASS。
比赛 worker CI 尚未证实通过。

---

## 补充说明

- 关联 Issue：#3913
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：feat/yafc-1.3.7
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：基础库任务 #12242；HD1–HD4 当前均有否定证据，按 B 类申报，不以轮次/等待时间声称高难。
- 知识增量：按源码 #ifdef/defined 与实际 AC_DEFINE/config.h 语义验证空值存在性宏；依赖真实缺失、数值宏及类型宏不能套用。四区检索对比 es-shell/optional-dep 草稿，无等价解决方案；配套 KV/MD 随同一软件提交。
- 完整 SSH/SFTP 生产路径和依赖保留，但 SFTP、IPv6 端到端业务未验证，不列为通过项。
- NLS/Kerberos 当前自动探测未找到；OpenSSL Base64 能力不等于 FTPS/TLS，不宣称这些能力适配完成。
- 尚未合并或发布；只有合并后进入平台正式 /release，PR 验证不上传制品。

### 2026-10-12 临时目录兼容修复

OHOS 的旧 config.status 两条临时目录创建分支已定向修复：私有 TMPDIR、创建时 umask007+mkdir，保留 cleanup 与全部上游测试。事务 `yafc-w3-20261012-hmdfs-tmp-recipe-r3` 单次启动，官方 W3 本地 CI exit0，完整12回执及释放 PASS；上游 0/0（无注册上游测试，make check 仍执行），安装消费者 6/6 通过。原始完整日志 SHA256 `629d330931e04fa55ed92491eb9640b818fe290ca012b0b6492d19b2c14e0214`。
完整 finish 原生RC1，只保留 step5b/step8 后置失败，不改写为整体PASS。
配套知识已补充当前验证边界；比赛 worker 的 CI、AI Review、合并和发布需要针对新提交另行确认。
本轮不声称验证 SFTP 服务；消费者覆盖已声明的 FTP 流程和已安装命令行行为。
本轮仅恢复临时目录策略修改前的 configure 时间戳，保留 VTI 依赖规则和发布文档，完整 make check 不跳过。
