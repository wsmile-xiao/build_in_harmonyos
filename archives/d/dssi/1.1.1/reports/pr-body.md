## PR 信息

- **三方库名称**：dssi
- **上游版本**：1.1.1
- **上游仓库地址**：https://dssi.sourceforge.net/
- **适配路径**：路径 A（基础适配）+ 路径 B（知识库扩展）
- **使用知识库**：新增草稿 E14859-draft-2501（待主编审核）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 1 | Automake `make check` 的 `tests/controller`；与 `tests/Makefile.am` 及结果摘要核对。 |
| 集成测试 | 0 | 上游未单独注册。 |
| 其他测试 | 0 | 上游未单独注册。 |
| **合计** | **1** | 真机执行 1/1。 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 1 | 不变 | 原样执行 controller。 |
| 集成测试 | 0 | 不变 | 无上游注册用例。 |
| 鸿蒙特有测试 | 1 | +1 | `test_package` 使用已安装的 DSSI 公共头和包依赖。 |
| **合计** | **2** | **+1** | 上游 1/1；新增消费者 1/1，分母分开记录。 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

补丁仅将导出的 `dssi.h` 对 ALSA 私有子头引用改为公共 umbrella header；未改变上游测试逻辑。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

新增的 `test_package` 仅验证安装后公共头及依赖闭包，不计入上游测试。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：1/1（100%）
- 新增测试用例通过率：1/1（100%）
- 本轮真机事务：`dssi-repair-w3-20261010T101340Z`；12/12 回执、干净 Conan RC0、上游1/1及消费者1/1。原始日志 SHA-256：`892a57d171d130d075480f74be33b713142c6566462f429591c793d5707cf3d6`。
- 修复 CI #80114：移除仅为定位 helper 而要求 ambient Automake 的逻辑，绑定 release helper 与编译器实测 tuple；对2009 config.sub四个精确锚点补充三段/四段OHOS识别，漂移和错误tuple明确报错。已有草稿补充helper来源与解析边界，全部测试保留。
- 比赛 worker CI 和平台 AI Review 须对修复后的当前 HEAD 重跑；此处不预称 CI 通过。

---

## 补充说明

- 关联 Issue：#3746
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/dssi-1.1.1
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 其他说明：知识草稿 `knowledge/drafts/E14859-draft-2501.kv` / `.md` 说明导出头依赖私有子头时须修正源头并用已安装包消费者验证；合并后执行 `/release`。

### 2026-10-12 临时目录兼容修复

OHOS 的旧 config.status 两条临时目录创建分支已定向修复：私有 TMPDIR、创建时 umask007+mkdir，保留 cleanup 与全部上游测试。事务 `dssi-w3-20261012-hmdfs-tmp-substep-r2` 单次启动，官方 W3 本地 CI exit0，完整12回执及释放 PASS；上游 1/1（100%），安装消费者 1/1 通过。原始完整日志 SHA256 `217916e1725afb6847438ea5b7b0d0e92ee4dab5d78865e6128e7133984d85c7`。
本轮调用未改动的官方 finish W3 子步骤，不宣称完整 finish 已全部通过；前一完整 finish 的归档/验证失败记录保留。
配套知识已补充当前验证边界；比赛 worker 的 CI、AI Review、合并和发布需要针对新提交另行确认。


### 2026-10-13 当前 CI 修复

Autoconf can select the mksh print builtin while detecting the configure interpreter, then execute config.status under Bash where print does not exist. That breaks generated Libtool contents even though configure returns success. Use a declared Bash tool consistently for configure and generated-helper execution.

当前真机事务 `dssi-ci-repair-w3-20261013-r2`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `d2b51f0f9ab024025676c7bb4d7466940ccfc8e7756172a96207952c0d64ed7a`。上游 1 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
