# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_cfe0e833.md`

---

## 背景

- **软件名称**: gulkan
- **版本**: 0.15.1
- **构建日期**: 2026-08-29
- **构建系统**: meson
- **上游仓库**: https://gitlab.freedesktop.org/xrdesktop/gulkan/-/archive/0.15.1/gulkan-0.15.1.tar.gz
- **适配路径**: 路径 A（基础适配）
- **补丁数量**: 3
- **编译依赖**:
- glib/2.84.0.1
- gdk-pixbuf/2.44.6.1
- graphene/1.10.8
- cairo/1.18.4
- vulkan-headers/vulkan-sdk-1.4.357.0
- zlib/1.3.1.1
- **最终状态**: 成功

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖从源码准备到 PR 提交的完整链路。以下是关键节点的执行情况：

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| init-build | 源码下载/解压 | 完成 | |
| build | 编译构建 | 成功 | 构建系统: meson |
| conan-verify | 配方验证 | 通过（第 10 轮） | 依序排雷：zlib 冲突→版本线对齐→meson [binaries]→签名加载→VkFormat 上游 bug→库名 -0.15→transitive headers→test() cwd/VirtualRunEnv |
| finish | 归档收尾 | 完成 | |
| submit | PR提交+AI检视+CI | PR #7121 AI检视✅ + CI✅（第3次构建） | 前两次 CI 失败：git-clone 基础设施抖动 + worker 缺 llvm-ar（配方已修） |

### 失败与问题

- **1**: 根因=版本冲突 zlib/1.3.1 vs 1.3.1.1（originates glib2/2.88.0）, 解决方案=graphene 拉 glib2（钉 1.3.1 无 -fPIC），gdk-pixbuf/cairo 拉 1.3.1.1（-fPIC，E005/E234）
- **2**: 根因=`meson: libintl_gettext: symbol not found`（meson 自身崩）, 解决方案=曾 tool_requires(glib) 取 glib-compile-resources；VirtualBuildEnv 把 glib 的 proxy libintl.so.8（只导出 g_libintl_*）前插 LD_LIBRARY_PATH，遮蔽 hnp python 需要的真 gettext libintl（musl: LD>RUNPATH）
- **3**: 根因=`gnome.compile_resources: Could not get pkg-config variable`, 解决方案=conan 生成的 gio-2.0.pc 无 glib_compile_resources pkgvar，meson find_tool 在 pkgconfig 分支抛异常（未走 PATH 兜底）
- **4**: 根因=`gulkan-texture.c:50 VkFormat from void* [-Wint-conversion]`, 解决方案=上游 bug：`self->format = VK_NULL_HANDLE`（VK_NULL_HANDLE 是 `((void*)0)`，VkFormat 是枚举）
- **5**: 根因=test_package dlopen `libgulkan-0.15.so.0: Permission denied`（errno13）；glib-compile-resources exec `Operation not permitted`, 解决方案=OHOS 设备对安装包目录未签名 ELF 施加强制代码签名（手册 §7 ELF 签名；chmod 无效=SELinux 域）
- **6**: 根因=test() `self.run([exe])` → sh 127；相对路径 cwd 不对, 解决方案=列表被 shell 当字面量；basic_layout 产物在 build 根但 cwd 非该目录
- **7**: 根因=库名/include 写成 gulkan-0.1, 解决方案=制品实为 api_version=0.15（`libgulkan-0.15.so`，include/gulkan-0.15）

### 知识图谱使用情况

- **引用知识条目**: 无
- **新增知识草稿**: 6 条
- **引擎命中情况**: 草稿目录 234 条
- **测试统计**: 总计 0, 通过 0, 失败 0, 跳过 0
- **未覆盖的错误模式**: ①tool_requires(glib)→proxy libintl 遮蔽 hnp python 真 libintl，meson 启动即崩（E 库无命中，引擎只报 E001/E298 噪音）②OHOS 设备强制 ELF 签名：未签名 .so dlopen EACCES / 下载的 bin exec EPERM ③CI worker PATH 缺 llvm-ar，meson project() 挂 ④VK_NULL_HANDLE 赋 VkFormat 枚举=上游真 bug

### AI 检视结果

- **检视阶段到达**: —
- **变更摘要评估**: 无必须修改点（单包，配方+3 patch+测试）
- **检视意见数量**: 0
- **检视意见处理**: 无需处理

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: 未知
- **CI 失败原因**: 无

### 效率分析

- **HANDOFF 次数**: submit 阶段 1（PF0 环境闸 str/str 框架 bug，OHC_PREFLIGHT=0 按文档绕过）；conan-verify 失败 9 轮均非 HANDOFF 路径（直接读日志修复）
- **重试次数**: conan-verify ×10、CI ×3（1 次 infra git-clone、1 次 llvm-ar、1 次绿）
- **关键瓶颈**: meson/Qt6/OHOS 三层运行时坑无知识库条目，全靠 readelf/最小复现逐层剥离（llvm-ar 那层耗时最久：本地无法复现 CI PATH 差异）
- **耗时较长的步骤**: G2 每轮 conan create 3-6 分钟 ×10；W4 审计两轮（首轮抓出 conandata file:// P0——finish close-archive 会重写 URL，提交前必查）
<!-- EVENTS:BEGIN -->
### 过程事件时间线（自动记录，v12.10）

共 2 个事件（含 1 次 HANDOFF、0 次推进/恢复），由 harness 各闸门自动累积：

| 时间 | 事件 | 详情 |
|------|------|------|
| 2026-08-29T12:19:23 | handoff:git_commit_failed | git commit 失败:  |
| 2026-08-29T12:24:42 | skeleton_created | result_partial |
<!-- EVENTS:END -->
---

## 建议

### SKILL 设计改进

1. finish 的 close-archive 重写 conandata 为 file:// predl 缓存后**不还原**，且该状态可被直接提交（本次被 W4 审计判 P0 返工）——建议 finish 结束时自动还原并只留 .bak。
2. preflight PF0 `_git_toplevel()` 返回 str 与 `repo_dir / d` 拼接崩溃（str/str），create-pr 唯一咽喉点被打上 --no-preflight 依赖。
3. submit 的 commit 步骤把 "no changes added to commit"（存在无关脏文件时）误判为失败——worktree 共享 libXext 脏改的本仓库必现，建议兼容该文案。
4. 建议 CI 失败评论附带各步骤 stderr 摘要（本次 llvm-ar 错误藏在"查看完整日志"的 SPA 里，get-comments 截断 24k 字符，diagnose 归类为"网络问题"误导）。

> 针对 SKILL 流程设计、门禁机制、HANDOFF 机制等方面的改进建议。
> 例如：某步骤门禁过于严格/宽松、流程顺序不合理、缺失某个检查环节等。

### 模板改进

1. 缺 meson/OHOS 模板：建议 templates/conanfile-meson.py.tmpl 内置 `_library_runtime_env`（QML2_IMPORT_PATH/LD）+ `[binaries] ar/ranlib 绝对路径` + `tool_requires(glib)` 反模式警示注释。
2. test_package 模板应强制 `VirtualRunEnv` + cwd 说明（本次两个包都栽在 LD 注入）。

> 针对 conanfile.py 模板、PR body 模板、test-report 模板等方面的改进建议。
> 例如：模板缺失某些字段、自动填充覆盖率不足、占位符过多等。

### 自动化补全

1. PF4 依赖探测已拦"未发布 requires"，但拦不住"已发布但图内 package_id 无二进制/依赖漂移"（zlib 1.3.1 vs 1.3.1.1 冲突要到 conan create 才炸）——建议 PF4 增加 `conan graph info` 干跑。
2. ELF 签名/加载类失败（EACCES）可自动识别为环境策略并提示 selfSign 方案（本次 30 分钟人工定位）。
3. recipe-search 建议索引 awf-gtk 的 zlib override 先例（当时靠 grep archives 手工找到）。

> 针对需要人工介入的环节，提出自动化改进建议。
> 例如：某些检查可以自动化、错误恢复可以更智能、依赖解析可以更完善等。

### 知识图谱覆盖

未命中 4 类新错误（建议入库）：①glib proxy-libintl LD 遮蔽→meson 崩 ②OHOS ELF 未签名 dlopen EACCES/exec EPERM→package() selfSign ③CI worker PATH 无 llvm-ar→MesonToolchain.binaries 绝对路径 ④VK_NULL_HANDLE→VkFormat 枚举赋值 clang 硬错误。

> 针对知识图谱未覆盖的错误模式，建议新增哪些 E-entry。
> 例如：本次遇到的新错误模式应该沉淀为知识条目等。

---

## 作者

- **姓名**: wanderlust_0823
- **邮箱**: wanderlust_0823@noreply.gitcode.com
- **Agent ID**: A745
- **生成时间**: 2026-08-29 12:24:42
- **PR 编号**: —
- **Git Commit**: 2ebbccba3
