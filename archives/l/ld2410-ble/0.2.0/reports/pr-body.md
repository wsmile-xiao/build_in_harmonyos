# feat(ld2410-ble): 0.2.0 适配 HarmonyOS PC

## PR 信息

- **三方库名称**：ld2410-ble
- **上游版本**：v0.2.0
- **上游仓库地址**：https://github.com/930913/ld2410-ble
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：openharmony-compile-agent 技能（build_in_harmonyos）；引用既有条目 E466（源码归档布局陷阱）、E512（纯 Python 包 CI 依赖解析）、E090（平台检测 harmonyos/linux 不一致）、E319（python wheel/site-packages/PYTHONPATH）；本次新增草稿 E585、E586

> ld2410-ble 是与 HLK-LD2410B / LD2410C 24GHz 毫米波存在感应雷达模块通信的
> 纯 Python 异步 BLE 客户端库（poetry-core 构建后端、`src/` 布局、无 C 扩展）。
> 本 PR 交付 Conan 配方 + 测试接入，**不修改任何上游源码与测试文件**。

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1 | 来源：上游 pytest 套件 `tests/test_init.py::test_add`（仅断言 `import ld2410_ble` 可导入） |
| 集成测试 | 0 | 上游无集成测试 |
| 其他测试 | 0 | 无 |
| **合计** | **1** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 44 | +43 | 43 项新增消费者单元断言（`test_package/test_ld2410_ble.py`：构造真实 LD2410B/C 通知帧，经库 API 与 `_notification_handler` 断言解码结果 —— 目标状态位、移动/静止距离与能量、探测距离、工程模式 8 门能量数组、`intify` 小端转换、常量契约、回调注册/触发/注销、分包缓冲重组）+ 上游 1 项原样执行 |
| 集成测试 | 0 | 不变 | 上游本无集成测试 |
| 鸿蒙特有测试 | 20 | 新增 | `test_package/test_ld2410_ble_ohos.py`：OHOS 运行时契约（`platform.system()=="HarmonyOS"` / `sys.platform` 属 OHOS 族 `linux|ohos`（设备/桌面构建报 linux、CI worker 报 ohos，双实测）/ aarch64 小端）、纯 Python 安装免原生工具链校验、运行期依赖导入完整性、bleak 默认 BLE 后端平台缺口显式探测 |
| **合计** | **64** | **+63** | 上游 1 项 + 新增 63 项 |

> 计数口径：64 = 上游 1 + 新增消费者单元 43 + 新增鸿蒙特有 20，无重复计数；
> 全部为可独立判定的断言用例（每条来自 `test_package` 的检查点输出）。

---

## 上游测试用例修改说明

**是否存在对上游测试用例的修改？**

- [x] **否**，未修改上游任何测试用例

上游 `tests/test_init.py` 以 vendored 方式**逐字节原样**接入
（`test_package/tests/test_init.py`），在包安装环境中由 `test_package` 内的
subprocess 调用 pytest 执行，未做任何改写、跳过或断言弱化。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **是**，上游测试覆盖严重不足，适配后补全了测试

- **补全的测试范围**：库核心数据解码面 43 项单元断言 + 鸿蒙平台运行时契约 20 项
- **补全原因**：上游测试套件仅含 1 个用例（`tests/test_init.py::test_add`，
  仅断言包可导入），完全没有覆盖帧解析、能量门、回调、缓冲重组等本库的实际功能面，
  无法证明适配后库在 HarmonyOS PC 上可用。
- **新增测试文件清单**：
  1. `test_package/test_ld2410_ble.py` — 消费者单元测试（43 项断言）：以真实的
     LD2410B/C 通知帧驱动库的解析路径，断言状态位/距离/能量/门数组/intify 字节序，
     以及回调与分包缓冲行为；发 `HMBS_TEST_PACKAGE_RESULT=43/43`。
  2. `test_package/test_ld2410_ble_ohos.py` — 鸿蒙特有测试（20 项断言）：断言 OHOS
     运行时契约（HarmonyOS 平台标识 + `sys.platform` 属 OHOS 族 `linux|ohos` + aarch64 小端）、纯 Python
     产物免原生工具链、运行期依赖可导入，并**显式探测** bleak 后端在 HarmonyOS 的
     平台缺口（接受"可用/明确报错"两种真实结果，不做 stub 掩盖）；发
     `HMBS_OHOS_TEST_RESULT=20/20`。
  3. `test_package/tests/test_init.py` — 上游套件的原样接入（1 项，`pytest` 执行）；
     发 `HMBS_UPSTREAM_TEST_RESULT=1 passed`。

---

## 验证结果

### 编译验证

- 编译器：不适用（纯 Python 库，无原生编译环节；由 Conan 管理的 Python 3.12 运行时执行安装）
- 编译状态：**通过**（`conan create` 返回 0；W3 本地 CI 模拟 setup.sh + build_and_test.sh 通过）
- 构建系统：pip（上游 `poetry-core` 构建后端）+ Conan 2.29.1，profile `ohos-aarch64`
- 配置选项：`python -m pip install . --prefix=<build_folder>/stage`（不引入任何 C/C++ 编译依赖）

### 产物验证

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | ✅ | `conan create` RC=0，三层测试全绿 |
| 产物存在性 | ✅ | 私有 prefix 下 `lib/python3.12/site-packages/ld2410_ble/` 完整（含 `ld2410_ble.py`、`const.py`、`models.py`、`exceptions.py`） |
| ELF 格式 | N/A | 纯 Python 包，无 `.so`/`.pyd` 二进制产物，故无 ELF 检查项 |
| 运行测试 | ✅ | 64/64 通过（100%），详见 `reports/test-report.md` |
| 动态依赖 | ✅ | 运行期依赖 bleak / bleak-retry-connector / async-timeout 由 pip 经 `pypi.cnb.cool` 镜像解析安装；无动态库链接面 |

### 补丁说明

**0 个补丁。** 上游源码零修改（`patches/` 为空，`conandata.yml` 的 `patches` 为空）。
配方不做 `replace_in_file`、不做平台宏 `#ifdef` 包装。

### 依赖

| 依赖 | 版本约束 | 来源 |
|------|---------|------|
| bleak | >=0.19.0 | pip（`pypi.cnb.cool` 镜像）；制品仓无该配方 |
| bleak-retry-connector | >=2.3.0 | pip（同上） |
| async-timeout | >=4.0.1 | pip（同上；`async-timeout/5.0.1` 制品仓已发布，但为与上述两个 BLE 依赖保持单一解析路径仍走 pip） |

三者均为纯 Python 包，不引入 OHOS 原生工具链依赖。

### 测试结论

- 总体评价：**通过** —— 上游 1/1（100%）、新增 63/63（100%），合计 64/64（100%）
- 已知限制：bleak 的默认 BLE 后端在 HarmonyOS 不可解析
  （`platform.system()` 返回 `"HarmonyOS"`，而 bleak 仅接受 `"Linux"`），
  故**真实 BLE 连接需平台/上游支持**；本包在 OHOS 上完整可用的是数据解码面与
  纯 Python 安装面。该缺口由鸿蒙特有测试显式探测并在 `notes.md`「R40 适配完整性
  人工确认」章节如实披露，未做 stub 掩盖。另：bleak 的 `dbus-fast` 依赖 wheel
  marker 为 `platform_system == "Linux"`，在 HarmonyOS 下被 pip 跳过。

### 遇到的问题与解决方案

1. **W3 本地 CI 模拟假失败（`can't create temp file for here document: read-only file system`）**
   —— 根因是 zsh 的 here-document 走 `TMPPREFIX`（默认 `/tmp/zsh`）而非 `TMPDIR`，
   而本平台 `/tmp` 为只读 erofs 挂载，与构建本身无关。解决：导出
   `TMPPREFIX=<可写目录>` 后再运行 `finish`/`submit`（`workflow_checks._run` 复制
   `os.environ`，无需修改框架脚本）。已沉淀为知识草稿 **E586**。
2. **9 个"新增文件"幻影补丁导致 G0 失败** —— `.orig` 基线被源码目录探测缺陷破坏
   （误把 `docs/Makefile` 判为源码根），使逐字节一致的工作树被比对出"新增"文件，
   生成的补丁在 G0 应用即 FAILED。解决：从官方归档重建干净 `.orig` 基线，`diff -rq`
   证实工作树与上游逐字节一致 ⇒ 零补丁，清空 `patches/`。已沉淀为知识草稿 **E585**。
3. **`conandata.yml` 被 W3 预下载流程改写为 `file://` 本地缓存路径** —— 提交前发现
   并还原为官方 GitHub tag archive URL + 原始 sha256。
4. **首轮 CI 失败（#60393）：鸿蒙特有测试误把 `sys.platform` 当作稳定平台判别** ——
   CI worker 实测 `sys.platform=="ohos"`（设备/桌面构建为 `"linux"`），原断言
   `sys.platform == "linux"` 因此在 CI 侧失败（19/20 passed），且 CI 侧把它误分类为
   "网络问题（源码下载超时）"。解决：以 `platform.system()=="HarmonyOS"` 作严格判别
   （这也是 `bleak` 选择 BLE 后端所依据的字段），`sys.platform` 仅要求属 OHOS/POSIX 族
   `in ("linux","ohos")`；并在本地强制 `sys.platform="ohos"` 复跑套件确认 20/20。
   该修正属**判别口径修正，非削弱断言**（未删除、未跳过、未放宽任何检查点），
   修复后 CI #60408 校验通过（worker OpenHarmonyPCDeveloper-CI-040）。

### 验证命令

```
# 配方构建 + 三层测试（纯 Python，无编译依赖）
conan create archives/l/ld2410-ble/0.2.0 --build \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=default

# 上游测试套件（vendored，原样执行）
pytest test_package/tests/test_init.py

# W3 本地 CI 模拟（finish 内嵌）
TMPDIR=$HOME/tmp TMPPREFIX=$HOME/tmp/zsh \
  python3 $SKILL_ROOT/scripts/ohc-run.py finish ld2410-ble 0.2.0 built
```

---

## 补充说明

1. **适配路径 B（贡献创新）**：本 PR 除配方与测试外，新增两条知识草稿——
   **E585**（refresh-patch 幻影补丁：`.orig` 基线损坏时零修改包也会产出补丁）
   与 **E586**（zsh here-document 使用 `TMPPREFIX` 而非 `TMPDIR`，`/tmp` 只读平台上
   CI L0 门禁假失败）。两条均为本次实测踩坑，且不被既有条目覆盖。
2. **需人工确认适配完整性（R40）**：本库属「外设/蓝牙」域，编译通过 ≠ 适配完成。
   本 PR 交付的是纯 Python 安装面与完整的数据解码面；真实 BLE 连接面受限于
   bleak 上游对 HarmonyOS 的识别（见「已知限制」）。同域先例
   `archives/a/airthings-ble/1.2.0` 具相同缺口且已合入 main，口径一致。
3. **源码来源选择**：上游 PyPI sdist 不含 `tests/`，无法满足"完整运行上游测试"的要求，
   故 `conandata.yml` 使用官方 GitHub tag archive（含 `tests/`），sha256 经实测校验。
4. **无 `commands.json`**：本包产物不含可执行文件（纯库），按 R38 无需声明。
5. **版本号**：首次适配上游版本，按 R37 使用 `0.2.0` 无适配修复后缀。
