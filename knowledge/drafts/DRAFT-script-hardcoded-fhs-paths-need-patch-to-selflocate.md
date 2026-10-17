# DRAFT-script-hardcoded-fhs-paths-need-patch-to-selflocate — 纯脚本包硬编码 FHS 绝对路径时，`DESTDIR` 只改安装前缀、改不了脚本内部

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-11
> **Severity**: 🟡 medium | **Category**: packaging / shell / conan / install-layout

## 相关既有条目（同族差异化定位）

| 既有条目 | 同族点 | 本 skill 的增量（差异化） |
|---------|--------|--------------------------|
| **DRAFT-script-selflocate-layout-mismatch**（bork）| 同属"纯脚本包交付布局"问题 | 那条的脚本**已有**自定位（`BASH_SOURCE` 推导），但 conanfile 的安装布局与之**不匹配** → 修法：**让布局去适配已有的自定位**。本条的脚本**根本没有**自定位，全是硬编码 `/usr/...` → 修法：**patch 脚本、引入自定位**。方向相反、互补 |
| **E188** | 都涉及 `make install` 这一步 | E188 讲 OHOS 的 toybox `install` 功能受限（`make install` **能否执行**）；本条讲**即使 install 成功**，脚本内部写死的绝对路径依然指不到包内 |
| **E043** | 都涉及脚本路径推导 | E043 讲 `${BASH_SOURCE[0]}` 在 toybox sh 下返回空 → **所以**本条的方案必须用 POSIX 的 `$0`，不能用 BASH_SOURCE |

> 查证（2026-09-11）：`SHAREDIR` / `脚本自定位` / `self-locating script` / `busybox install` 命中 **各 0 条**；`DESTDIR` 命中 49 条但均未讲"改不了脚本内部字符串"这一区分；本条为空白领域。

## Scope（何时用）

打包**无编译的纯脚本包**（POSIX shell / bash 工具、Debian 原生包）时，脚本顶部把 FHS 路径**写死为绝对路径**，随后 `source` / `.` 这些路径下的伴随文件。

### ⚠️ 先判类别（决定修哪个）

| 现象 | 类别 | 该修什么 |
|------|------|---------|
| 脚本**已**用 `$(dirname $0)` / `BASH_SOURCE` 自定位，仍失败 | **布局不匹配** | 修 conanfile 的 `package()`（见 DRAFT-script-selflocate-layout-mismatch）|
| 脚本**根本没**自定位，全是 `/usr/...` 硬编码 | **本条** | **patch 脚本**，引入自定位 |

判别命令：

```bash
grep -nE 'dirname|BASH_SOURCE' <src>/<script>   # 有输出 → 属布局不匹配类
```

## 根因

### 实测证据（cron-apt 0.13.0.1 的 `src/cron-apt`）

```bash
LIBDIR="/var/lib/cron-apt"              # :194
SHAREDIR="/usr/share/cron-apt"          # :195  ← 唯一影响「加载」的一处
ACTIONDIR="/etc/cron-apt/action.d"      # :223
ACTIONCONFDIR="/etc/cron-apt/config.d"  # :224
MAILMSGDIR="/etc/cron-apt/mailmsg.d"    # :225
MAILONMSGSDIR="/etc/cron-apt/mailonmsgs"      # :226
SYSLOGONMSGSDIR="/etc/cron-apt/syslogonmsgs"  # :227
REFRAINFILE="/etc/cron-apt/refrain"     # :228
ERRORMSGDIR="/etc/cron-apt/errormsg.d"  # :230
SYSLOGMSGDIR="/etc/cron-apt/syslogmsg.d" # :231
LOGMSGDIR="/etc/cron-apt/logmsg.d"      # :232
LOGDIR="/var/log/cron-apt"              # :233
APTCOMMAND="/usr/bin/apt-get"           # :257
...
. $SHAREDIR/functions                 # :294  ← 加载伴随的辅助函数
```

**共 13 处硬编码**（实测 `grep -cE '^[A-Z_]+="/' src/cron-apt`），全部指向包外的系统位置。

> ⚠️ 按影响分层：**只有 `SHAREDIR` 会导致「脚本根本跑不起来」**（`:294` 用它加载 `functions`）；其余 12 处多在运行期读写 `/etc`、`/var/log`，影响的是功能而非加载。

### 关键认知：`make install DESTDIR=<pkg>` 救不了它

- `DESTDIR` 只能把**安装动作**的目标前缀重定向到包内目录
- **改不了脚本文件内部写死的那个字符串**

→ 脚本运行时**仍旧**去 `/usr/share/cron-apt/functions` 找：

```
.: /usr/share/cron-apt/functions: No such file or directory
```

### 为什么 CI 可能还是绿的

若 `test_package` 只断言"文件存在于包内某处"，而**从不真实执行脚本**，缺陷就不会暴露 —— 典型**假通过**（对比 bork 那次同类教训）。

## 方案（patch 脚本 → 自定位 + 环境变量覆盖）

在 `conanfile.py` 的 `source()` 里 patch，改成**双层回退**（POSIX 兼容）：

```sh
if [ -n "${PKG_SHAREDIR:-}" ] ; then
    SHAREDIR="$PKG_SHAREDIR"                                          # ① 环境变量覆盖
else
    SHAREDIR="$(cd "$(dirname "$0")/../share/<pkg>" 2>/dev/null && pwd -P)"  # ② 脚本自定位
    [ -d "$SHAREDIR" ] || SHAREDIR="/usr/share/<pkg>"                 # ③ 系统路径兜底
fi
```

### 五个要点

1. **用 `$0`（POSIX），不要 `${BASH_SOURCE[0]}`** —— 后者是 bash 扩展，toybox sh 下为空（E043）
2. **保留系统路径兜底** —— 使脚本在"装到系统前缀"的部署方式下仍可用
3. **提供环境变量覆盖**（如 `CRON_APT_SHAREDIR`）—— 便于测试与自定义布局
4. **一并处理写日志/读配置类路径**（如 `LOGDIR` / `ACTIONCONFDIR`）—— 否则运行时仍会因 `/etc`、`/var/log` 不可写而失败
5. **配套：不调用 `make install`** —— OHOS 无 coreutils `install`（E188）；改由 conan 的文件工具按 patch 后的布局直接复制落盘。**避免"patch 推导出的布局"与"Makefile 安装的布局"两套逻辑打架**

```python
# conanfile.py — 用 conan 文件工具替代 make install
copy(self, "cron-apt", src=os.path.join(sf, "src"),
     dst=os.path.join(pf, "bin"), keep_path=False)
copy(self, "functions", src=os.path.join(sf, "src"),
     dst=os.path.join(pf, "share", "cron-apt"), keep_path=False)
```

## 备选（fallback）

若不便 patch 脚本（多脚本共享同一常量、或上游频繁变更），可改走"让绝对路径真的存在"的路线：装 GNU coreutils（E188 方案 2）+ 借助 `DESTDIR`/prefix 把文件放到脚本期望的位置。

但 conan 包**不允许写系统绝对路径**，该路线只在"包内模拟前缀 + 运行时注入"时成立，复杂度与脆弱性都高于 patch —— **且必须真实执行脚本验证**，不能只断言文件存在。

## 禁止

- ❌ **以为"加了 `DESTDIR` 就算适配"**：`DESTDIR` 改不了脚本内部的绝对路径字符串 → 包能装但不可用
- ❌ **`test_package` 只断言文件存在**：纯脚本包必须**真实执行**，否则假通过
- ❌ **用 `${BASH_SOURCE[0]}` 做自定位**：toybox sh 下为空（E043），纯 sh 包不可用

## 实证

- **cron-apt/0.13.0.1（PR #9592）**：`src/cron-apt` 实测 **13 处**硬编码 FHS 绝对路径（其中 `SHAREDIR`（`:195`）是唯一影响加载的一处）；`:294` 用 `. $SHAREDIR/functions` 加载伴随文件。OHOS 无 coreutils `install`（E188）→ 配方不调 `make install`，改用 conan 文件工具落盘；`SHAREDIR` patch 为脚本自定位（`dirname $0` 上一级 + `share/cron-apt`）+ `CRON_APT_SHAREDIR` 覆盖。
  - 结果：`conan create` **EXIT=0**；`test_package` **真实执行** `cron-apt --help` → PASS（输出 `USAGE: cron-apt [-i] [-s] [configfiles]`）
  - 上游测试 `test/test.sh` **3/3 PASSED**（该测试不依赖 apt，故可真实运行）
