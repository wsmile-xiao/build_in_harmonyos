# KB-ATBOOT — 老旧 autotools tarball 构建引导缺失（config.guess/sub + maintainer-mode）

## 一句话

2008~2015 年代的上游 autotools 源码包，普遍存在**构建引导层缺陷**：tarball 不含
`config.guess`/`config.sub`、内嵌 `umask 077` 的 config.status 在 HMDFS 上半途失败、
patch 后 maintainer-mode 时间戳倒挂触发 missing automake。本 SKILL 自动检测三类特征
并注入修复，让这些老库在 OHOS aarch64 上正常 configure。

## 触发场景（适用库范围）

满足任一条件的库大概率命中：

| 特征 | 典型库（已实证） |
|---|---|
| tarball 无 `config.guess`/`config.sub`（2008 前后 automake 惯例） | srf 0.1 |
| configure 内嵌 `umask 077` 建临时目录（HMDFS 700 目录不可写） | srf 0.1, io_lib 1.14.9, commoncpp2 1.8.1 |
| patch 触碰 Makefile.am 导致 mtime 倒挂（设备无 automake 无法重生成） | io_lib 1.14.9（E248 已入知识图谱，本 SKILL 的 fix.sh 一并覆盖） |

**检测特征（自动，无人工干预）**：

- 源码通道：configure 所在目录及其 build-aux/config/autoconf/aux/scripts 子目录
  缺 `config.guess` 或 `config.sub`
- 源码通道：`Makefile.in: Makefile.am` / `configure: configure.ac` mtime 倒挂
- 日志通道：`cannot guess build type` / `unable to guess system type` /
  `missing automake` / `automake-N.N: command not found`

## 使用方法

```bash
# 1. 检测（只读；退出码 0=健康 1=缺引导脚本 2=时间戳倒挂 3=两者）
detect.sh --src <源码目录> [--log <构建日志>] [--json]

# 2. 修复（幂等；config.guess/sub 从本目录 vendor/ 注入 + umask 022 + mtime 对齐）
fix.sh --src <源码目录>

# 3. 复现验证（两阶段：关 SKILL 复现报错 → 开 SKILL 编译通过）
reproduce.sh --sample <样例源码目录> [--keep] [--json]
```

conan 配方集成（conanfile.py 的 `build()` 内、`apply_conandata_patches` 之后）：

```python
import subprocess
kb = os.environ.get("KB_ATBOOT_DIR")  # 或直接内联 fix.sh 内容到配方
if kb and os.path.isdir(kb):
    subprocess.run(["bash", os.path.join(kb, "fix.sh"), "--src", self.source_folder], check=False)
```

更简做法：把 fix.sh 的三个动作直接写进 conanfile.py（见样例库 srf 的配方注释）：

1. `cp vendor/config.guess vendor/config.sub <src>/ && chmod 755`
2. `sed -i 's/umask 077/umask 022/g' <src>/configure`
3. `touch -r <src>/Makefile.am <src>/Makefile.in`（及 configure:configure.ac 对）

## 处理策略（②）

| 命中 | 策略 | 说明 |
|---|---|---|
| A：缺 config.guess/sub | **vendor 注入** | 官方 autoconf 归档脚本随本 PR 入仓（`vendor/`），无 fork、无本地路径依赖 |
| B：umask 077 | **sed 替换 022** | 与 commoncpp2/io_lib 0002 补丁同源；HMDFS 下 chmod 被忽略，只能改 umask |
| B：mtime 倒挂 | **utime 对齐** | 被生成者 mtime 对齐到生成者，掐断 missing automake 重生成（E248 处方） |

**不采用**的策略及原因：

- `env_unsupported` 标记：三类问题均可机械修复，不需要放弃适配
- `autoreconf -fi`：设备无 automake/aclocal，且会引入不可控重生成
- `--build/--host` 手工指定：违反 autotools-patterns 禁令（R15 家族）

## 复现脚本说明（③）

`reproduce.sh` 内嵌两阶段对照：

1. **阶段①（关 SKILL）**：原样 configure。srf 样例的失败模式是
   **rc=0 假成功但 Makefile 全部缺失**（config.status 写 ./confXXXX 失败）——
   老 autotools 包 configure 经常假成功，判定口径是"Makefile 是否生成"，不看退出码。
2. **阶段②（开 SKILL）**：detect → fix → configure → Makefile 生成成功。

**SIGPIPE 规避**：所有输出重定向到 `$WORK/*.log` 文件，绝不用 `cmd | head`
（SIGPIPE 会杀掉整条管道并掩盖真实退出码）。结果从日志文件与 `$?` 采集。

## 限制与不适用场景

- **只修引导层**：库源码本身的编译错误（如 musl API 缺失、C++ ABI 问题）不在本
  SKILL 范围——configure 过了之后 make 失败请查知识图谱其他条目
- **vendor/config.guess 版本**：2018 年代脚本，覆盖 aarch64-linux-ohos 判定已验证；
  若上游是更老的 configure（如 2005 前 AC_CANONICAL_SYSTEM 旧宏），注入脚本可能
  因接口不匹配无效，此时需按 E007/E160 手工 patch
- **umask 修复只针对 077**：其他 umask 值不在替换范围
- **不碰 conan 补丁管线**：mtime 对齐在 `apply_conandata_patches` 之后执行，与
  E248 处方一致；若配方本身用 E248 的 os.utime 方案则二者取其一即可
- **非 autotools 构建系统不适用**：cmake/meson 包不需要 config.guess

## 文件清单

```
kb-atboot/
├── README.md        # 本文档
├── detect.sh        # ①检测（源码+日志双通道，只读）
├── fix.sh           # ②修复（vendor 注入 + umask + mtime，幂等）
├── reproduce.sh     # ③复现（两阶段对照，SIGPIPE 规避）
└── vendor/
    ├── config.guess # 官方 autoconf 归档脚本（随 PR 入仓）
    └── config.sub
```

## 样例库验证结果（④）

样例：srf 0.1（Debian pool `srf_0.1+dfsg.orig.tar.gz`，PF7 合规官方源）

| 阶段 | 结果 |
|---|---|
| 检测（未修复） | `HIT-A: missing config.guess,config.sub`（rc=1） |
| 复现 phase1（关 SKILL） | `reproduced`（rc=0 假成功，Makefile/src/Makefile/test/Makefile 全缺失） |
| 修复 | `FIX-A: injected config.guess + config.sub` + `FIX-B: umask 077→022` |
| 复现 phase2（开 SKILL） | `fixed`（Makefile 三件全部生成） |

关联：知识图谱 E248（mtime 倒挂单条）由本 SKILL 的 fix.sh 覆盖并扩展为三类特征
一站式处理；E007/E160（config.guess 不认识 OHOS）是"有脚本但不认识平台"，本 SKILL
是"根本没有脚本"——互补不重叠。
