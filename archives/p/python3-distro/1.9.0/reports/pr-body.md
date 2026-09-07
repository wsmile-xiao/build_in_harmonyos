- **三方库名称**：python3-distro（distro）
- **上游版本**：1.9.0（2023-12 发布，当前最新稳定版）
- **上游仓库地址**：https://github.com/python-distro/distro
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（纯 Python noarch，参考仓库内 alabaster 1.0.0 先例模式）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 158 | 来源：pytest，tests/test_distro.py（收集 234 项，含参数化重复计数） |
| 集成测试 | 0 | — |
| 其他测试 | 0 | — |
| **合计** | **158** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 158 | 不变（上游套件原样保留） | OHOS 实测：1 passed, 233 skipped（见下方说明） |
| 集成测试 | 0 | — | — |
| 鸿蒙特有测试 | 12 | 新增 | test_package/test_distro_consumer.py：上游 resources 模拟数据同源断言 + OHOS 本机行为 + CLI |
| **合计** | **170** | **+12** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：上游 158 用例中 root_dir 模拟解析类（TestOSRelease/TestDistroRelease 等）被上游 `IS_LINUX = sys.platform.startswith("linux")` 门卫在 OHOS（sys.platform=="ohos"）上整类跳过（实测 233 skipped）。核心解析逻辑本身平台无关，故在 test_package 携带上游 resources/distros 的 4 个发行版子集（arch/ubuntu14/centos7/centos5），以**与上游测试同源的构造方式与期望值**补全 12 项消费者测试。
> - **补全原因**：上游门卫以 sys.platform 判定只在 Linux 上跑，跳过不代表逻辑在 OHOS 上不可用；为验证适配正确性，须有可在 OHOS 执行的等价断言。
> - **新增测试文件清单**：
>   1. `archives/p/python3-distro/1.9.0/test_package/test_distro_consumer.py` — 12 项：import/版本/归一化表、os-release 解析（arch/ubuntu14/centos7）、distro-release 文件解析（centos5 显式 release 文件）、unknown 发行版空值语义、best_version、repr、linux_distribution() 兼容 API、info()/os_release_attr、OHOS 本机行为（无 /etc/os-release 走 unknown 分支不抛异常）、CLI（python -m distro rc=0）。

## 验证结果

- 编译状态：通过（conan create 8 道门禁全过：G1 配方完整性/G2 干净构建/G3 系统库隔离/G4 产物完整性/L2/L4/L5；W3 本地 CI 模拟 L0-L5 全过，含 L1e 破坏性反向验证）
- 上游测试用例通过率：1/1（100%，执行项；233 项因上游 IS_LINUX 门卫在 OHOS 上跳过——0 失败 0 错误，属纯 Python 包的平台行为差异，非适配缺陷。核心逻辑已由下方新增测试覆盖）
- 新增测试用例通过率：12/12（100%）

## 补充说明

1. **上游套件 OHOS 实测**：`python3 -m pytest tests/test_distro.py -v` → `1 passed, 233 skipped in 0.35s`。唯一执行的 TestNonLinuxPlatform::test_cant_use_on_windows 通过（OHOS 上 import distro 成功，不触发 Unsupported platform）；233 项跳过全部因上游 `IS_LINUX = sys.platform.startswith("linux")`（OHOS 的 sys.platform=="ohos"）。
2. **OHOS 本机行为（如实记录）**：HarmonyOS 不提供 /etc/os-release、/etc/lsb_release 等标准发行版元数据文件，distro.id()/name()/version() 返回空串（unknown 分支），不抛异常——这是库对"无法识别的发行版"的既定语义，非适配缺陷。若 OpenHarmony 未来提供 /etc/os-release，distro 无需重新适配即可自动识别。
3. **构建方式**：纯 Python noarch（alabaster 先例）：`pip install --prefix staging` + site-packages 归一化 + console_script `distro` 入 bin/。运行时零依赖（setup.cfg 无 install_requires）。
4. **环境适配点**：build() 清除 PIP_TARGET/PIP_ONLY_BINARY（OpenDesk/CI worker 环境实测与 pip --prefix 冲突报 "Cannot set --home and --prefix together"）。
5. **测试防干扰**：本机 pip-global 可能已装同名 distro，test_package 把被测包 site-packages 作为首参传入，测试脚本硬断言 distro.__file__ 必须位于被测路径下（R34/L1e 合规，破坏性反向验证实测通过）。
