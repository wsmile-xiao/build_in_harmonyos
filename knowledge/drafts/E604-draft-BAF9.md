# E604 — autoreconf --install 重新注入带 umask 077 的 config.guess，仅修 configure 的 HMDFS umask 方案失效

## 错误特征
- `sh config.guess` / configure 阶段报 `unable to guess system type` 或
  `cannot guess build type; you must explicitly specify --build`，退出码 1；
- 完整日志尾部常伴随 `cannot create dummy.c: Permission denied` 或
  `mktemp: failed to create file via template '/tmp/cgXXXXXX': Permission denied`；
- 症状只在 HMDFS（/storage 挂载）上的全新构建（VPATH 新建目录）出现；
  已修补过 configure 的配方照样复现。

## 触发条件
- 构建系统: autotools（上游源码包**不带** configure/config.guess，仅 configure.ac，
  如 libmobi 0.12 的 GitHub tag tarball——`tar tzf` 确认无 config.guess/config.sub/configure，
  只有 configure.ac + autogen.sh）
- 阶段: 配方内引导阶段 `autoreconf --force --install`（日志证据：
  `configure.ac:22: installing './config.guess'`）

## 根因分析
上游包无 configure 时，配方必须 autoreconf 引导。`--install` 会从**当前 Automake
分发目录**（effective-path 解析到的 automake，如 conan automake/1.18 包的
`p/share/automake-1.18/config.guess`，2024-07-27 版）全新拷贝 config.guess/config.sub。
该分发版探测骨架为 `umask 077 && mktemp -d "$TMPDIR/cgXXXXXX"`：
- 在 HMDFS 上 UID 映射 + setgid 使 0700 临时目录对编译进程不可写，
  dummy.c 创建失败，config.guess 输出诊断信息并退出 1；
- 该文件**每次 VPATH 构建都被重新注入**，不是一次性产物。

因此 umask 修补若只打在 configure 上（configure 里同样有 umask 077 的
`$as_mkdir_p`/tmp 探测），configure 尚可过，但 config.guess 先于 configure 运行
（构建三元组探测），configure 一启动就因拿不到 build type 而死——修补顺序上
configure 的替换根本没机会生效。必须双文件同时处理。

注意与相近模式区分：
- E011：configure/config.status 的 umask 077（in-tree、configure 已存在，单文件修补够）；
- E175：autoreconf 重生成 configure（讲的是 maintainer 时间戳规则触发 autoconf 重跑）；
- 6048（babeltrace 草稿）错误 2：**make 阶段** automake maintainer 规则因
  configure.ac/aclocal.m4 比 configure 新而**重跑 autoconf**，再生成的 configure
  覆盖既有 umask 替换（证据 `configure~` vs `configure`），修复靠时间戳回拨——
  触发阶段（make vs 引导）、被覆盖文件（已修补 configure vs 全新注入的 config.guess）、
  修复边界（时间戳 vs 双文件 sed）均不同。

## 解决方案

### 推荐方案
在 `autoreconf --force --install` **之后**、`configure` **之前**，对 configure 与
config.guess 同时做 `umask 077 → umask 000` 替换，并用 `! grep` 断言两文件均无
残留（fail closed——Automake 分发版换代导致模式漂移时立即中断，而不是带病走到
HMDFS 权限错误再人肉排查）：

```bash
autoreconf --force --install -I m4
sed -i 's/umask 077/umask 000/g' configure config.guess
! grep -n 'umask 077' configure config.guess   # 断言无残留，非零即失败
```

### 回退方案
预置一份已修补（umask 000）且含 `__OHOS__` 分支识别的 config.guess/config.sub，
autoreconf 后覆盖回源目录（同时解决 umask 与平台识别两个问题；不可自动执行）。

### 禁止做法
- ❌ 只对 configure 单文件 sed umask：config.guess 的 dummy.c 探测在 HMDFS 0700
  临时目录内 Permission denied，configure 报 cannot guess build type 退出 1，
  每次 VPATH 构建复现；
- ❌ 把生成产物 config.guess 入库/checkout 对抗 --install 注入：automake 分发版
  升级后补丁过期，umask 与 __OHOS__ 平台识别双重漂移，难以审计。

## 验证
```bash
grep -c "umask 077" config.guess   # 期望 0（修补后）
sh config.guess                    # 期望输出构建三元组，退出码 0
# 端到端：conan create 走到 configure 正常产出的 "checking build system type..."
```

## 关联条目
- 相关: E011（umask 077 in configure/config.status）、E175（autoreconf 重生成
  configure）、DRAFT-6048（make 阶段 maintainer 规则重跑 autoconf 覆盖 umask 替换）
- 状态: draft（待 draft-review 预审与 promote）
