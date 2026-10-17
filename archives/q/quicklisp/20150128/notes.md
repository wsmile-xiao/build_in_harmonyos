# quicklisp 20150128 适配笔记

## 软件与版本

| 项 | 值 |
|---|---|
| 软件 | quicklisp（上游仓库 quicklisp/quicklisp-bootstrap） |
| 包版本 | 20150128（Debian 源码包版本目录；`20150128-2`） |
| 上游版本串 | 2015-01-28（`quicklisp.lisp:25` `qlqs-info:*version*`） |
| 上游地址 | https://github.com/quicklisp/quicklisp-bootstrap （tag `version-2015-01-28`） |
| 官网 | https://www.quicklisp.org |
| 许可 | MIT / Expat |
| 本质 | **Common Lisp 库管理器的自包含启动（quickstart）文件**，单文件 57144 bytes |

## 编译环境

- 构建系统：**无**（上游 `Makefile` 只有 `all:` 空目标与 `tag:` 发版目标）
- 编译日期：2026-09-29
- Conan：2.29.1（OHOS 适配版，`os=OHOS` 枚举）
- Profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS / os.version=6.0 / arch=armv8 / clang 15 / libc++ / cpp17 / Release）
- 状态：built

## 适配路径（为什么是"无构建/打包族"）

1. 上游 `Makefile` 全文（137 bytes）只有两个目标：
   - `all:` —— **空目标**，`make` 不产生任何产物；
   - `tag:` —— 发版时给 `quicklisp.lisp` 打 `version-<日期>` tag（依赖 git 工作区干净）。
2. 上游无任何 C/C++ 源码（文件清单仅 `LICENSE.txt` / `Makefile` / `README.txt` / `quicklisp.lisp`），
   Debian 源码包同样标注 `Architecture: all`、`Build-Depends: debhelper-compat` 且 `debian/rules` 仅
   `dh $@` —— 即只在安装阶段把 `quicklisp.lisp` 拷到 `/usr/share/common-lisp/source/quicklisp`。
3. 因此本配方**不定义 `build()`**：既无编译可做，也不允许用伪造的编译命令假装构建（R34）。
   产物 = 包内 `share/quicklisp/` 下的启动文件 + 说明 + OHOS 运行期辅助脚本；`package_id()` 清空
   （内容与 os/compiler/arch 无关，单一 package_id 服务所有 OHOS 架构）。

## 编译步骤

```bash
# 1) 依赖预检（W0）：本包无第三方依赖（N=0）
bash ci/scripts/preflight_check.sh quicklisp/20150128 --deps ""

# 2) 源码获取与核验
#    tarball: https://github.com/quicklisp/quicklisp-bootstrap/archive/refs/tags/version-2015-01-28.tar.gz
#    sha256 : 92aef100970de4e64b102be1f08de1c9a9e8f22d6711f6aad217ffb6d16fc82f（13942 bytes）
#    内含 quicklisp.lisp sha256 = 4a7a5c2aebe0716417047854267397e24a44d0cce096127411e9ce9ccfeb2c17
#    （与官方发布端点 https://beta.quicklisp.org/quicklisp.lisp 逐字节一致）

# 3) 语言预检（R47）
python3 scripts/ohc-run.py lang-preflight quicklisp 20150128 --src <BUILD_SRC_DIR>
#    -> detected=c（由顶层 Makefile 判定），与任务语言 cpp 同族兼容

# 4) 无编译：直接进入 conan 配方验证
python3 scripts/ohc-run.py conan-verify quicklisp 20150128
```

## 上游测试（R51 三步法）

**第一步 · 清点**：上游无 `tests/` 目录、无 ctest/pytest 注册、无 `check`/`test` make 目标：

```bash
cd <src> && make -n check   # -> "make: *** No rule to make target 'check'."  (exit 2)
cd <src> && make -n test    # -> "make: *** No rule to make target 'test'."   (exit 2)
cd <src> && make            # -> 空目标 all:，无输出（exit 0），无产物
```

**结论：上游没有自动化测试套件（0 个自动化用例）。**

**第二步 · 真实入口执行**：上游 `README.txt` 给出的唯一使用入口是「启动 Lisp，然后
`(load "quicklisp.lisp")`」。用制品仓内的 `ecl/24.5.10`（Common Lisp 实现，OHOS/armv8）
真实执行：

```bash
cd <ecl_pkg>/lib/ecl-24.5.10      # ohpcd 的 ecl 以 prefix=/ 构建，*load-path* 为空，
                                  # (require 'sockets) 需在模块目录下运行（见下方"注意事项"）
ecl -norc \
  -eval '(load "<pkg>/share/quicklisp/quicklisp.lisp")' \
  -eval '(format t "~&QLQS_VERSION=~A~%" qlqs-info:*version*)' \
  -eval '(format t "~&QUICKSTART_INSTALL=~A~%" (if (fboundp (find-symbol "INSTALL" "QUICKLISP-QUICKSTART")) "present" "missing"))' \
  -eval '(quit)'
```

输出：

```
;;; Loading #P".../quicklisp.lisp"
;;; Loading #P".../lib/ecl-24.5.10/sockets.fas"

  ==== quicklisp quickstart 2015-01-28 loaded ====

    To continue with installation, evaluate: (quicklisp-quickstart:install)
    For installation options, evaluate: (quicklisp-quickstart:help)

QLQS_VERSION=2015-01-28
QUICKSTART_INSTALL=present
```

**第三步 · 如实申报**：上游自动化用例 0，功能入口 1（加载成功）；test_package 另设 4 个
消费者用例（见下）。

## 鸿蒙（OHOS）相关改动

1. **架构无关打包**：`package_id()` 清空 —— 包内容为纯文本 `.lisp`，与 os/compiler/arch 无关，
   单一 package_id 服务所有 OHOS 架构（对应 Debian `Architecture: all`）。
2. **运行期环境契约**：`package_info()` 通过 `runenv_info`/`buildenv_info` 暴露
   `QUICKLISP_BOOTSTRAP`（包内启动文件绝对路径），消费者无需猜测包内路径：
   `(load (uiop:getenv "QUICKLISP_BOOTSTRAP"))`。
3. **HOME 缺失回退（鸿蒙特有）**：`quicklisp.lisp:1571` 把 client 默认安装目录定义为
   `(merge-pathnames "quicklisp/" (user-homedir-pathname))` —— 依赖实现能解析 HOME。
   OpenHarmony PC 默认用户目录为 `/storage/Users/currentUser`，但沙箱/服务方式拉起的进程
   可能没有 HOME。随包分发 `ohos/quicklisp-ohos-env.sh`：source 一次即导出
   `QUICKLISP_HOME`（默认 `${HOME}/quicklisp`；HOME 缺失时回退
   `/storage/Users/currentUser/quicklisp`）与 `QUICKLISP_BOOTSTRAP`。

> 本包产物无 ELF，因此**不涉及** ELF 签名（与含可执行文件的包不同）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 下载源码时报 `SSL: CERTIFICATE_VERIFY_FAILED` | 本机 Python 没有默认 CA bundle（`ssl.get_default_verify_paths()` 的 cafile 为空） | 设置 `SSL_CERT_FILE=/etc/ssl/certs/cacert.pem`（环境级，非配方改动） |
| 2 | 本机 conan 2.32.0 报 `Invalid setting 'OHOS' is not a valid 'settings.os' value` | 本机装的是官方 conan，不含 `os=OHOS` 枚举；SKILL §0.0 要求用社区源 OHOS 适配版 | 从 `https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/` 安装 `conan==2.29.1`（OHOS 适配版）后使用 |
| 3 | ECL 加载 quicklisp.lisp 报 `Module error: Don't know how to REQUIRE SOCKETS` | `quicklisp.lisp` 的 ECL 分支有 `(:prep (require 'sockets))`；ohpcd 的 ecl 包以 `prefix=/` 构建 → `*load-path*` 为空，找不到 `sockets.fas` | 在 ECL 模块目录（`<ecl_pkg>/lib/ecl-24.5.10`）下运行 ecl（test.sh 已固化该步骤） |
| 4 | `finish` 的 W3 报 `PermissionError: [Errno 13] Permission denied: 'zsh'` | 本机 OHOS 沙箱无法 exec `/usr/bin/zsh`（EACCES，缺 libncursesw/libtinfo 且系统库不在本命名空间）；且 CPython 在 HarmonyOS 上对无目录名的命令强制走 `os.posix_spawn`（`_IS_HARMONYOS` 分支，不做 PATH 搜索）；候选循环遇 EACCES 即致命中止，PATH 中靠后的可用 zsh 永远轮不到 | 安装 cmd-pkgs 预编译 `zsh 5.9`（`/storage/Users/currentUser/usr/local/bin/zsh`），并把其目录置于 `run_local_ci` 子进程 PATH 最前（`finish` 调用带 `cwd`，走 fork+exec 候选列表） |
| 5 | W3 内 `build_and_test.sh` 报 `can't create temp file for here document: read-only file system` | OHOS `/tmp` 只读（SKILL §7 gotcha E002）；zsh here-document 需要临时文件（bash 用管道故不受影响） | 运行 finish 前导出 `TMPDIR=/storage/Users/currentUser/tmp` 与 `TMPPREFIX=$TMPDIR/zsh` |
| 6 | 每次 W3/CI 运行后 `conandata.yml` 被改写为 `gh-proxy.com` 镜像 URL 列表并遗留 `.orig` | 框架时序缺陷：`ci/conan/build_and_test.sh:1029` 先做镜像回退改写，`:1181` 才把（已污染的）内容备份给 `trap EXIT` 还原 | 每次运行后手工还原为唯一官方 https 源；已作为框架缺陷记录 |

## 依赖版本

无第三方依赖（N=0）。运行期需要一个 Common Lisp 实现（语言运行时，非本包依赖）：
本仓制品仓已提供 `ecl/24.5.10`（OHOS/armv8，含 gc/gmp/libffi/ncurses/readline）。
test_package 用其真实加载启动文件。

## 验证结果

```bash
# 消费者用例（test_package，真实执行）
sh test.sh <pkg>/share/quicklisp <ecl_pkg>
# => SUMMARY total=4 passed=4 failed=0 skipped=0
#    其中 ohos-env-helper / ohos-ecl-load 为鸿蒙特有用例（2 个）

# 配方验证
python3 scripts/ohc-run.py conan-verify quicklisp 20150128
```

## 交付物

| 文件 | 说明 |
|------|------|
| `share/quicklisp/quicklisp.lisp` | 上游启动文件（57144 B，sha256 4a7a5c2a…2c17） |
| `share/quicklisp/README.txt` | 上游说明 |
| `share/quicklisp/quicklisp-ohos-env.sh` | OHOS 运行期环境辅助脚本（HOME 缺失回退） |
| `licenses/LICENSE.txt` | 上游许可（MIT） |

## 注意事项

- 消费者需自备 Common Lisp 实现；本配方不把语言运行时写进 `requires()`
  （quicklisp 本体只是与架构无关的启动文件）。
- 上游启动过程默认走**明文 HTTP**（启动文件 `quicklisp.lisp` 第 1588 行附近的
  `*quicklisp-hostname*` 指向 `beta.quicklisp.org`，其 URL 由 `http` 拼接），
  首次 `install` 需可访问该域名；这属运行期网络资源，非构建/库依赖，与 conandata 源 URL 无关。

## 本地环境记录（W3 可运行性修复）

`finish` 的 W3 门禁要求用 `zsh` 执行 `ci/conan/setup.sh` + `ci/conan/build_and_test.sh`。
本机为 OHOS 沙箱，需两项环境适配才能真实运行（**均为环境侧，未改动任何框架文件**）：

1. **zsh 可执行性**：本沙箱不能 exec `/usr/bin/zsh`（EACCES；其 `libncursesw.so.6`/`libtinfo.so.6`
   不在本命名空间内），且 CPython 在 HarmonyOS 上对无目录名的命令强制走 `os.posix_spawn`
   （`subprocess.py`：`... or _IS_HARMONYOS`），不做 PATH 搜索；候选循环遇 EACCES 即中止。
   → 安装 cmd-pkgs 预编译 `zsh 5.9` 到 `/storage/Users/currentUser/usr/local/bin/zsh`，
   并让 ohc 子进程 PATH 以该目录开头（W3 的调用带 `cwd`，走 fork+exec 候选列表）。
2. **here-document 临时文件**：OHOS `/tmp` 只读（E002），zsh here-doc 需临时文件。
   → 运行 finish 前导出 `TMPDIR=/storage/Users/currentUser/tmp` 与 `TMPPREFIX=$TMPDIR/zsh`。

验证结果（真实 zsh + 真实 CI 脚本）：

```bash
TMPDIR=/storage/Users/currentUser/tmp TMPPREFIX=$TMPDIR/zsh \
  python3 $SKILL_ROOT/scripts/ohc-run.py finish quicklisp 20150128 built
# Step 5/10: [1/2] setup.sh ✅  [2/2] build_and_test.sh ✅ → "W3 本地 CI 模拟通过"
# → finish 写入 .ci-result.json (exit_code=0, integrity_hash=917e8123ee1836e1,
#   log_sha256=75361b92d04675515df76c653247818dc163b94e5586a7792a71fea0213c80e9)
#   并落盘 reports/w3-local-ci.log；manifest.yaml → built
```
> finish 整体退出码仍为 1：剩余两步为**非阻塞/框架侧**问题 ——
> `step5b` 因仓内既有知识条目 `E219/E253/E305` 必填字段为空（最近修改于 2026-08-20 的
> v12.4 提交，非本次新增）；`step8`（submit 就绪预检）要求 `packaging/`（与 R20
> 「禁止手动打包」冲突）与 `.staging-verified`（JC5 未白名单的遗留标记，全仓仅 4 例
> 且均属已污染文件）。两项均未创建，避免制造 JC5/R20 违规。
---

**编译结束**: 2026-09-29 21:33
**最终状态**: built
