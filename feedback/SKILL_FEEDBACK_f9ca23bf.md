# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_f9ca23bf.md`

---

## 背景

- **软件名称**: knewstuff
- **版本**: 6.14.0
- **构建日期**: 2026-08-29
- **构建系统**: cmake
- **上游仓库**: https://download.kde.org/stable/frameworks/6.14/knewstuff-6.14.0.tar.xz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 3
- **编译依赖**:
- qtbase/6.11.1
- qtbase-gui/6.11.1
- qtdeclarative/6.11.1
- karchive/6.18.0
- kconfig/6.18.0
- kcoreaddons/6.18.0
- ki18n/6.18.0
- kwidgetsaddons/6.18.0
- kpackage/6.18.0
- attica/6.18.0
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: cmake |
| conan-verify | 配方验证 | 通过（第 8 轮） | 依序排雷：kpackage 版本线冲突→Qt6 分包 Qml 解析→I18nQml 守卫→ELF 签名加载→LD 注入语义→CWD 农场→断言真实语义 |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | PR #7154 AI检视✅ + CI✅(#34435，2m43s) | create-pr 504 超时=**假失败**（第 3 次遇到，list API 核实已成）；注意 CI 随 PR 创建自动触发，/rebuild 常属多余 |

### 失败与问题

- **1**: 根因=`find_package(Qt6 COMPONENTS Qml)` 报 `Could NOT find Qt6Qml (missing: Qt6Qml_DIR)`，CMAKE_PREFIX_PATH 加包根/lib/cmake 都无效, 解决方案=qtbase 的顶层 `Qt6Config.cmake` 只在**自身目录树**解析组件；Qml/Quick/QuickWidgets 属 qtdeclarative 独立发布包
- **2**: 根因=`KF6::I18nQml target not found`（widgets 与 tools 两处 PRIVATE 链接）, 解决方案=已发布 ki18n（6.14/6.18/6.26 全系）`BUILD_WITH_QML=OFF`（当时 Qt6 Qml 未发布，前提现已过时）
- **3**: 根因=版本冲突 karchive 6.18 vs 6.14, 解决方案=kpackage 仅发布 6.18.0，其图钉死 kcoreaddons/ki18n/karchive=6.18.0
- **4**: 根因=test_package 运行 `符号 not found`（QApplication 等）, 解决方案=`Environment.append("LD_LIBRARY_PATH", [list])` 把 Python list 字面量拼进环境变量
- **5**: 根因=主包安装后 `libKF6NewStuffWidgets.so` 的 NEEDED 是 `../../bin/libKF6NewStuffCore.so` 相对路径, 解决方案=KF6 目标库无 SONAME 时 lld 把链接入参路径原样记入 NEEDED；musl 对含 `/` 的 NEEDED 按**进程 CWD** 解析
- **6**: 根因=测试断言 `entry.setStatus(Downloadable) → isValid()` 失败, 解决方案=臆写断言。真实语义：`isValid()` 只看 uniqueId 非空

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 5 条
- **引擎命中情况**: 草稿目录 234 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: ①Qt6 分包组件解析报"Could NOT find Qt6Qml"时 CMAKE_PREFIX_PATH 全部无效，唯一正解 QT_ADDITIONAL_PACKAGES_PREFIX_PATH ②已发布 ki18n 全系无 QML add-on（消费方 if(TARGET)+__has_include 守卫，另发【依赖项】补全）③conan Environment.append(name,[list]) 字符串化产生假"符号缺失"④KF6 无 SONAME 时 lld 把相对链接路径记入 NEEDED，musl 按 CWD 解析→test() 必须 cwd=bindir ⑤cpp_info.bindirs=["bin"] 静态触发 L0k/R38（无产物也报）

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 摘要准确覆盖三 patch+双测试；无必须修改点
- **检视意见数量**: 0（✅ 未发现问题）
- **检视意见处理**: 无需处理

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: 3（G2 configure×1、G0 老 tarball×1 非阻塞、W3 commands_json_r38×1），另有 create-pr 假超时人工核实×2
- **重试次数**: conan-verify×8、W3 finish×2、create-pr 核实×1（未盲重）
- **关键瓶颈**: 本机 ~/.conan2 被前期 conan download/remove 探测污染后 Invalid 假象干扰判断约 2 小时——正确姿势应第一时间切独立 CONAN_HOME（~/tmp/ch/home）再排查
- **耗时较长的步骤**: 每轮 conan create 3-6 分钟×8；干净 home 全量依赖下载 ~4 分钟（qtdeclarative 等一次性）

<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 1 个事件（含 0 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-08-29T23:33:29 | skeleton_created | result_success |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. PF4 依赖探测应按"实际 requires 引用名"查仓（qt6-declarative/qml 等别名搜不到导致误判"未发布"，qtdeclarative 实已在仓，直接影响 knewstuff 可行性评估数小时）。
2. ohc 各子命令建议默认打印 CONAN_HOME 路径并在检测到主缓存近期有 download/remove 动作时提示"建议独立缓存验证"。
3. create-pr 超时后的"假失败"应内置复核：脚本捕获 TimeoutError 后自动 list 一次再报错（本仓库第 3 次踩同坑）。
4. W3 的 commands_json_r38 探测建议改用产物事实（package/bin 是否非空）而非配方静态 bindirs，纯库包声明 bindirs 即误伤。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. KF6 模板（conanfile-kf6 建议新增）应内置：六件套 + QT_ADDITIONAL_PACKAGES_PREFIX_PATH 块 + farm/cwd test() + _self_sign_elfs（本包与 ktextwidgets/kxmlgui 三份配方高度同构，可整段固化）。
2. test_package/MANIFEST.yml 模板补 upstream_test_note 字段（登记平台侧测试门控差异，如 if(LINUX)）。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. refresh-patch --auto 已可靠；建议 finish 后自动跑"conandata file:// 还原+校验"（gulkan 的 P0 教训同样适用本包——本次靠手工 grep 拦截）。
2. 建议 finish 支持 --conan-home 透传（本次需手工 export CONAN_HOME 绕过主缓存污染）。
3. CI 自动触发认知更新到 SKILL：PR 创建即触发构建（23:18:05 建、23:20:48 绿），trigger-ci /rebuild 多数场景多余。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

建议入库 4 条（均已写包内 notes.md）：①QT_ADDITIONAL_PACKAGES_PREFIX_PATH=Qt6 分包组件唯一解 ②Environment.append list 字符串化→假符号缺失 ③无 SONAME→相对 NEEDED→musl CWD 语义（farm+cwd 方案）④ki18n 无 QML add-on 的消费方守卫 + ki18n/6.18.0.1【依赖项】补全路径。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: wanderlust_0823
- **邮箱**: wanderlust_0823@noreply.gitcode.com
- **Agent ID**: E1A9
- **生成时间**: 2026-08-29 23:33:29
- **PR 编号**: —
- **Git Commit**: d224798f5
