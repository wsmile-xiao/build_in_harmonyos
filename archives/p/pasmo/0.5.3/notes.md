# pasmo 0.5.3 适配笔记

## 编译环境
- 构建系统: autotools（上游发行包自带 configure〔GNU Autoconf 2.60〕+ Makefile.in + install-sh/missing/depcomp）
- 编译日期: 2026-09-21
- 编译器: clang 15（来自 conan profile；设备上为 Harmonybrew OHOS SDK clang，目标 aarch64-linux-ohos）
- 状态: built（conan-verify G0–G4 全绿；上游 0 用例〔已清点〕；test_package 22/22）

## 编译步骤
```bash
# 探索编译（模式 B）——VPATH 构建保持 .work 干净
mkdir -p $HOME/work/kasumizawa-miyuu/tmp/pasmo-vpath-build && cd $_
sh $BUILD_SRC_DIR/configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX          # 安装 bin/pasmo
make check                                  # 上游空目标：0 用例（R51 证据）

# Conan 配方验证
python3 scripts/ohc-run.py conan-verify pasmo 0.5.3 --profile ohos-aarch64-device
# 内部 conan create 真实执行：
#   source(): 下载官方 .tgz（sha256 db3c41ca…f87f1eb）+ 应用 0001-configure.patch
#   build():   上游 configure + make -j1 + make check（空目标）
#   test_package: sh test_pasmo.sh → 22/22 断言（真实执行已安装二进制）
```

## 上游测试清点（R51 申报，N=0）
| 项 | 结果 |
|----|------|
| tests/ 等测试目录 | 无（`.orig` 69 个文件中无 tests/test/Test 目录） |
| Makefile.am TESTS/check_PROGRAMS | 无（仅 `bin_PROGRAMS = pasmo`） |
| configure 测试开关 | 无（仅 AC_PROG_CXX + AC_CONFIG_FILES） |
| `make check` 实际执行 | 0 用例（automake check-am 空目标：`Nothing to be done for 'check'`） |
| 备注 | 34 个 `*.asm` 是 EXAMPLE_ASM 示例（EXTRA_DIST）；上游测试套件自 0.5.5 才加入 |

按竞赛规则：上游无测试（N=0）→ 如实申报并以 `test_package/test_pasmo.sh` 补全消费者回归（22 条断言，见 MANIFEST.yml）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure` 运行到 config.status 生成 Makefile 阶段报 `./confXXXXXX/subs-1.sed: Permission denied`，Makefile 未能生成 | configure 生成的 config.status 以 `umask 077` 创建临时目录；HMDFS 上 0700 目录对构建进程不可写（知识 E011，retry 同款坑） | 补丁 `0001-configure.patch`：两处 `umask 077` → `umask 022`（mktemp -d 与 mkdir 回退分支），无平台宏/无前缀注入（PF5/PF6 合规） |
| 2 | 上游发行包没有 config.guess/config.sub，configure 却可正常运行 | pasmo 的 configure.ac 只有 AC_PROG_CXX + AC_CONFIG_FILES，无 AC_CANONICAL_HOST → configure 不做 build/host 规范化，不需要这两个辅助文件 | 无需处理；未使用 `--build/--host/--target` 绕过（R41 精神），测试环境同时验证了本机与 `--host=aarch64-linux-ohos` 形态均可 configure |
| 3 | `pasmo --version` 报 `ERROR: Invalid option`，CI L2 冒烟探测（--version/--help）失败 | 上游 0.5.3 没有这两个开关（无参数时打印 `Pasmo v. 0.5.3` 横幅） | 平台 L2 为**非阻塞**告警（CI 脚本：`[warn] L2: ... failed (non-blocking)`，L2_RESULT 保持 skip）；如实记录，不作伪。消费者测试改为断言无参数横幅 |
| 4 | `--prl` 生成报 `ERROR: PRL genration failed: out of sync`（rc=1） | 上游 PRL(RSX) 导出要求程序覆盖 0x100–0x1FF 页，小样例不满足；纯上游行为，与平台无关 | 不作为测试断言；在 manifest/notes 记为已知上游限制 |
| 5 | `conan create` 的 `source()` 下载官方 `.tgz` 失败：`RemoteDisconnected('Remote end closed connection without response')`（curl 同 URL 正常） | pasmo.speccy.org（2009 年的老站点）按 User-Agent 拒绝 Python 默认客户端（python-requests / python-urllib），curl/wget 形态可用 | 配方 `source()` 的 `get()` 传入 `headers={"User-Agent": "curl/8.8.0"}`；URL 与 sha256 不变（R39），下载内容字节一致 |

## 源码修改

仅 1 个可移植性补丁（不改变任何程序语义、无平台宏）：

- `patches/0001-configure.patch`
  - **修改文件**: `configure`（config.status 生成段）
  - **修改原因**: HMDFS 上 `umask 077` 创建的临时目录不可写（E011），导致 Makefile 生成失败
  - **修改内容**: `(umask 077 && mktemp -d "./confXXXXXX")` → `(umask 022 && …)`；`(umask 077 && mkdir "$tmp")` → `(umask 022 && …)`
  - 未修改任何 C++ 源码、Makefile.am/in 或样例 .asm；补丁新增行不含 `__OHOS__`（PF5 合规），未触碰 `/usr/local`/SYS_PREFIX（PF6 合规）

## 依赖版本

无第三方依赖（W0：`requirements()` 为空，纯 C++ + libc）。构建期宿主工具：`make`、`sh`、clang 15（Conan 工具链）。

## 验证结果

```text
# 上游测试：0 用例（清点证据见上表与 test_package/MANIFEST.yml）
make check → "Nothing to be done for 'check'"（rc=0）

# test_package 消费者回归（sh test_pasmo.sh）：22/22 PASS（详见 reports/test-report.md）
# 逐字节比对：原始二进制 / Intel HEX / TAP / TZX / MSX / 8086；
# 容器：+3DOS / tapbas / Amsdos / CP/M 86 CMD；诊断/退出码/--err/-I/符号表/--nocase/--bracket
# conan-verify G0–G4 / L2 / L4 / L5：conan create 干净复现通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/pasmo | Z80 交叉汇编器（arm64 ELF） |
| licenses/COPYING | 上游 GPL-2.0 许可证原文 |

产物为可执行命令，已在软件级 `archives/p/pasmo/commands.json` 声明（R38）。

## 注意事项

- `pasmo` 无 `--version/--help`；如后续版本（0.5.4+）加入，需同步更新 L2 预期与测试。
- 消费者测试通过 `--name`/固定输出文件名使容器头字节确定；若上游变更容器格式，属上游行为变更，需按新行为更新断言并说明。
- 首次执行新二进制时设备可能弹安全确认框（R7）；本任务的设备验证均在解锁状态下完成。

## 对话记录

### 对话 #1 — 2026-09-21：pasmo 0.5.3 适配（feat/pasmo-0.5.3）

- 任务：pasmo 0.5.3（平台任务 #9323），路径 A 基础适配
- 过程：W0 依赖检查（无第三方依赖）→ init-build（官方 .tgz，sha256 `db3c41ca…f87f1eb`）→ lang-preflight（cpp 匹配）→ 探索编译（configure 受 HMDFS 权限影响，见问题 1，打 umask 补丁后通过）→ 手写消费者回归 22 条（逐字节）→ `conan-verify` G0–G4 全绿 → 本地 CI 门禁（L0/L1/L1e/L4/L5 PASS；L2 因上游无 `--version/--help` 为非阻塞 skip）→ `finish`（W2 结构 + R36 依赖 + W3 编译验证，`.ci-result.json` exit_code=0）
- 结论：`bin/pasmo` 功能与多格式输出逐字节验证通过；上游 0 用例已清点申报（R51）；源码仅 1 个 configure 可移植性补丁

---

**编译结束**: 2026-09-21 22:43
**最终状态**: built
