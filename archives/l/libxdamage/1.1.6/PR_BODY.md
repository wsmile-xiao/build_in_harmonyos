- **三方库名称**：libxdamage
- **上游版本**：libXdamage 1.1.6（对应 `libXdamage.so.1.1.0`）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libxdamage
- **适配路径**：路径 A（基础适配） + 知识库扩展（draft 知识解决一类问题）
- **使用知识库**：OHOS 下 X.Org autotools 库的通用工具链修复模式；头文件级依赖
  transitive_headers 消费（E340）、无 X server 消费者测试方法（E341）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：libXdamage 1.1.6 release tarball；源码无 `check_PROGRAMS`/`TESTS` |
| 集成测试 | 0 | 来源：`make check` 审计；无实质可执行上游测试 |
| 其他测试 | 0 | 上游仅生成库和文档/spec 目标 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游未提供单元测试套件 |
| 集成测试 | 0 | 不变 | 上游未提供集成测试套件 |
| 鸿蒙特有测试 | 2 | 新增 | `api_surface.c`（6 个导出符号强类型重定位）+ `version_contract.c`（Damage/XID、XDamageNotifyEvent 布局、XserverRegion），均不依赖 X server |
| **合计** | **2** | **+2** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

libXdamage 上游只发布源码与文档目标，无任何自动化测试。适配后新增两个
不依赖 X server 的消费者测试：`libxdamage_api_surface` 对 libXdamage.so.1
全部 6 个导出函数强制活重定位，确保 ABI 完整；`libxdamage_version_contract`
校验 Damage/XID 句柄、XDamageNotifyEvent 结构体布局与 Xfixes 的
XserverRegion 类型可用性。

## 知识库扩展

复用 E342 已验证的 X11 家族 autotools 适配模式。本 PR 补充两个新知识点：

1. **OHOS autoconf works-check 陷阱（关键，来自 libxrender/0.9.12 实证）**：
   本机模式（`--build == --host`）下 autoconf 的 C 编译器 works-check 会尝试
   *执行* conftest 二进制，被 OHOS 沙箱拦截报 `C compiler cannot create
   executables`（worker 相关、非确定性——libxdamage 曾 7 次 CI 全部在
   configure 期失败）。必须让 configure 进入交叉模式（`--host=aarch64-linux-ohos`
   且 build ≠ host），works-check 仅链接不运行即通过。
2. **config.guess/config.sub 补丁（必须，来自 libxrender/0.9.12 移植）**：
   config.sub（2021-08-14）不认识 ohos OS，需在合法 OS 列表加 `ohos*`、
   kernel-os 校验加 `linux-ohos*`；config.guess（2021-06-03）不认识
   HarmonyOS，fall through 到编译 dummy.c 探测（需在 TMPDIR 写文件）被沙箱
   拦截，需在 NetBSD 分支前插入 HarmonyOS 分支直接
   `echo aarch64-unknown-linux-ohos`。补丁按本包 config.guess/sub 版本
   hunk 适配。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（N/A，已手工核验 libXdamage-1.1.6 release tarball：无 `test/` 目录、根 `Makefile.am` 无 `check_PROGRAMS`/`TESTS`，`make check` 无可执行用例）
- 新增测试用例通过率：2/2（100%），`test_package` 由 GitCode CI 在 PR 上构建并执行通过（`libxdamage_api_surface` + `libxdamage_version_contract` 两个 consumer 均通过）

## 补充说明

- 本 PR 只新增 `archives/l/libxdamage/1.1.6/` 下的 Conan 配方、元数据、test_package，不修改依赖包或基础设施目录。
- 包名沿用小写 `libxdamage/1.1.6`；目录使用小写 `archives/l/libxdamage/1.1.6/`，符合 conan slug 规则。
- 上游测试用例统计已通过解包 libXdamage-1.1.6 release tarball 手工核验（无 `test/` 目录、无 `check_PROGRAMS`/`TESTS`），不存在少报。
