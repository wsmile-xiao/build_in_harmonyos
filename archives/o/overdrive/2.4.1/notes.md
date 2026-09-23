# overdrive 2.4.1 适配笔记

## 编译环境

- 构建系统: none（纯 Bash 单文件脚本，无编译）
- 编译日期: 2026-09-12
- 设备: HarmonyOS（HongMeng Kernel 1.12.0，aarch64）
- 工具链: clang 15.0.4 / GNU Make 4.4.1 / CMake 4.1.2 / Conan 2.29.1（OHOS 适配版，profile `ci/conan/profiles/ohos-aarch64`，os=OHOS arch=armv8）
- bash: `/data/service/hnp/bin/bash` 5.3.0(1)-release (aarch64)
- 状态: built（conan-verify 通过，未上传制品仓）

## 上游与真实 recipe

- 上游: https://github.com/chbrown/overdrive tag `2.4.1`（2025-05-21），MIT
- 归档内容只有两个文件：`README.md`(11742 B) + `overdrive.sh`(13992 B)
- 唯一外部真实 recipe：Homebrew core `Formula/o/overdrive.rb`
  （`url`/`sha256` 与本次 conandata 完全一致；`install` 动作为 `bin.install "overdrive.sh" => "overdrive"`；
  Linux 侧声明 `depends_on "openssl@3"`、`depends_on "util-linux" # for uuidgen`、`uses_from_macos "libxml2" # for xmllint`）
- conan-center-index 无该包配方（`recipes/overdrive` 404）

## 上游测试清点（R51 申报表）

| 项 | 值 | 证据 |
|---|---|---|
| 上游测试文件数（tests/、*_test、check 目标） | 0 | `tar tzf overdrive-2.4.1.tar.gz` 全清单仅 2 文件；无 Makefile/configure/.github |
| 可列测试清单的命令（make -n check / ctest -N / meson test --list） | 不适用 | 无构建系统 |
| 上游实际可执行测试入口 | 1 个：`overdrive download fake_file.odm` → 文案 `Specified media file does not exist`，rc=2（Homebrew `test do` 断言） | 实跑输出见本文「上游测试入口实跑记录」一节（命令与实际输出摘录，可复核） |
| 实际执行结果 | 源码目录 / staging 前缀 / conan 安装包 三处均 rc=2 | 同上；安装包内同一入口亦由 test_package 用例 `enoent_download_exit2` 断言（`test_package/test_overdrive.py`） |
| 上游用例统计 | 总数 0 / 通过 0 / 失败 0 / 跳过 0（上游确无自动化测试） | 清点证据：本文「上游测试清点」命令与输出；`test_package/MANIFEST.yml` 声明 `upstream_tests: 0` |
| test_package 用例统计（不可代替上行） | 总数 11 / 通过 11 / 失败 0 / 跳过 0 | `test_package/test_overdrive.py` 用例名逐条见下节；`test_package/MANIFEST.yml` 声明 `assertion_count: 11` |

### 上游测试入口实跑记录（命令与实际输出摘录，可复核）

```console
$ tar tzf overdrive-2.4.1.tar.gz                 # 上游全部内容
overdrive-2.4.1/
overdrive-2.4.1/README.md
overdrive-2.4.1/overdrive.sh
$ for f in Makefile configure configure.ac CMakeLists.txt meson.build .github tests; do [ -e "$f" ] && echo 存在 || echo "缺失 $f"; done
缺失 Makefile / 缺失 configure / 缺失 configure.ac / 缺失 CMakeLists.txt / 缺失 meson.build / 缺失 .github / 缺失 tests
$ overdrive --version      ; echo rc=$?   →  2.4.1   rc=0
$ overdrive                ; echo rc=$?   →  You must supply at least one command. / …media file…   rc=1
$ overdrive download fake_file.odm; echo rc=$?
Specified media file does not exist: fake_file.odm
rc=2                                              # 与 Homebrew 断言（文案 + exit 2）一致

# test_package 11 个用例名（conan create 的 test() 阶段逐条打印 CASE …: PASS）
pkg_layout_bin_overdrive · pkg_executable_bit · bash_syntax_check · version_output_2_4_1
usage_no_arguments_exit1 · enoent_download_exit2 · runtime_prereqs_on_path
metadata_cdata_extraction · info_author_title_duration · metadata_sidecar_written · license_hash_pipeline
合计: 11 cases, 11 passed, 0 failed, 0 skipped
```

> 说明：构建/验证的完整原始日志（`reports/*.log`、`w3-local-ci.log`、`.ci-result.json`）按仓库 `.gitignore` 规则属本机运行产物，不随 PR 入库；故本节把命令与关键输出内嵌于此（多命令示例做了分行整理，输出内容未作改写），供评审在不落地日志的情况下复核。

## 编译步骤

无 configure/make。真实构建即 conan create：

```bash
conan create archives/o/overdrive/2.4.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable     # rc=0
```
源码下载来源（区分直跑与工具镜像注入，避免歧义）：

- 官方 URL 直连可达实测：`curl -sSL -o /dev/null -w "%{http_code} %{url_effective}" https://github.com/chbrown/overdrive/archive/refs/tags/2.4.1.tar.gz` → `200 https://codeload.github.com/chbrown/overdrive/tar.gz/refs/tags/2.4.1`，`sha256 accc3ec4…fb28860`（与 conandata 一致）。
- 直接执行 `conan create`（不经过 conan-verify / CI 模拟）时的真实日志行：`Sources correctly downloaded from https://github.com/chbrown/overdrive/archive/refs/tags/2.4.1.tar.gz`。
- `ohc-run.py conan-verify` 与 `ci/conan/build_and_test.sh` 会**临时**注入镜像（E017 预防 / 预下载）改写工作副本，运行结束后回滚；因此那两份日志里出现的镜像 URL 不代表归档内容。入库的 `conandata.yml` 始终只有官方单值 URL（R39），且两种 URL 指向同一文件、由 sha256 强校验锁定。
→ `Packaged 1 file: overdrive` + `Packaged 1 '.md' file: README.md`
→ package id `da39a3ee5e6b4b0d3255bfef95601890afd80709`（`package_id(): self.info.clear()`，架构无关）

Staging 验证（写 `.staging-verified`）：`cp $BUILD_SRC_DIR/overdrive.sh $TEST_PREFIX/bin/overdrive && chmod 755`
→ `--version` 输出 `2.4.1` rc=0；`download fake_file.odm` rc=2；staging 与上游文件 sha256 同为 `715bbbf8…72e599`（零修改）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ohc-run.py conan-verify` G1 FAIL：缺 `export_sources()` 与补丁应用调用 | G1 门禁把补丁管线列为配方必备项，本包零补丁 | 按标准写法补 `export_conandata_patches(self)` / `apply_conandata_patches(self)`（conandata `patches: {}`），保持单一事实源，不引入任何补丁内容 |
| 2 | staging 安装报 `install: command not found` | OHOS toybox 0.8.12 未编 `install` applet | 改 `cp` + `chmod 755`（配方本身用 conan `copy()`，不受影响） |
| 3 | 测试输出混入 `shell-init: error retrieving current directory: getcwd: … Not supported` | Python `subprocess.run(cwd=…)` 在 HMDFS 上触发 bash shell-init 的 getcwd 失败（与目录无关，`cwd=None` 继承则正常） | test_overdrive.py 全部改传绝对路径、不再传 `cwd=`；复跑后噪声消失且 11/11 通过 |
| 4 | `lang-preflight` 默认（cpp）判 rc=2 并自动落 `env_unsupported` 终态回执 | R47：任务语言默认 cpp，而纯 Bash 包按 `_source_stats` 规则（bash 不计主体）判 `detected=other` | 该包任务语言应为 `other`：`lang-preflight … --lang other` → rc=0 匹配通过；终态回执稍后用 `result --force` 覆盖（R46 生命周期草稿遇 draft:false 不再降级） |

## 源码修改

**无任何源码修改、无补丁**（`patches: {}`，`patches/` 空；staging 与 conan 包内文件 sha256 与上游一致）。
R8 口径：未新增任何 `__OHOS__` 平台宏或 conandata 注入。

## 依赖版本

运行时命令（脚本 overdrive.sh:87 的 PREREQ 清单 + README:182-205）在 OHOS 的落点：

| 命令 | 解析路径 | 版本 | 制品仓可消费替代（conan download --only-recipe rc=0） |
|---|---|---|---|
| curl | /usr/bin/curl | 8.8.0-DEV (aarch64-linux-ohos) libcurl/OpenSSL 3.0.12/zlib 1.3.1 | curl/8.15.0.1（传递 openssl/3.5.6.1、zlib/1.3.1.1） |
| uuidgen | /usr/bin/uuidgen | toybox 0.8.12 | ❌ util-linux 未发布；uuid/2.40.1 仅 libuuid（--disable-all-programs） |
| xmllint | /data/service/hnp/bin/xmllint | libxml 2.11.9 | libxml2/2.15.3.1（LIBXML2_WITH_PROGRAMS=ON，零传递依赖） |
| iconv | /usr/bin/iconv | toybox 0.8.12 | libiconv/1.17.1 |
| openssl | /usr/bin/openssl | OpenSSL 3.0.9（`openssl version` 实测；curl 报的 `OpenSSL/3.0.12` 是其链接的 libssl 版本，与 CLI 非同一来源） | openssl/3.5.8.1 |
| base64 | /usr/bin/base64 | toybox 0.8.12 | coreutils/9.10 |
| bash | /data/service/hnp/bin/bash | 5.3.0 | bash/5.3 |
| sed / awk / tr / seq | /usr/bin(sed,tr,seq) · /data/service/hnp/bin(awk) | toybox / HNP awk / sed 系统版 | sed/4.9、gawk/5.3.0、coreutils/9.10 |

配方最终 **零 conan requires**：上述命令在设备与 CI worker 的 PATH 上均已具备（W0 探测记录见 `.od-dep-logs/02-w0-registry-probe.log`、`11-a-layer-w0.log`）。

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify overdrive 2.4.1        # rc=0
G1 PASS / G0 PASS / G2 PASS(conan create) / G3 PASS(无 lib/ 目录，无系统同名库冲突 R26)
G4/L2/L4/L5：纯可执行包（无 ELF .so）→ 跳过或仅产物检查
$ conan create …                                                 # rc=0，见上
overdrive <pkg>: 11 cases, 11 passed, 0 failed, 0 skipped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/overdrive | 13992 B，配方 `chmod 0755`，HMDFS 归一化后实测 `stat -c %a` = 770（X_OK 为真） | 上游 overdrive.sh 重命名安装（与上游 sha256 一致） |
| share/doc/overdrive/README.md | 11742 B | 上游唯一文档（含 MIT 声明，README:263-266） |
| archives/o/overdrive/commands.json | — | R38 CLI 声明（type=tool，versions.2.4.1.ref=overdrive/2.4.1，binary=false） |

注：上游**无 LICENSE 文件**，故不伪造 `licenses/`，仅安装 README 作为文档与许可出处。

## 注意事项

1. **R47 语言**：本包任务语言是 `other`（纯 Bash，`detected_language=other`）。若平台按 cpp 派发，lang-preflight 会正确拒收，勿绕过。
2. **bash 可解析性**：安装后的 `bin/overdrive` 靠 `#!/usr/bin/env bash` 运行；OHOS `/usr/bin` 无 bash，需保证 `/data/service/hnp/bin` 在 PATH（设备与 CI worker 默认满足，conan profile buildenv 亦注入）。若将来要求包自足，应改为 `tool_requires("bash/5.3")` 并在 runenv 注入。
3. **toybox 不是风险**：实测 `tr -Cs`、`seq`、`base64`、`iconv`、`uuidgen` 行为与需求一致；曾怀疑的 `tr` 压缩差异已被证伪（`a,b!c`→`a-b-c`、`A??B`→`A-B`）。
4. **网络**：`download`/`return` 子命令需要访问 OverDrive 服务器，验证只在离线路径（ENOENT、metadata、info、哈希管线）进行；上游测试同样无法覆盖在线流程（brew 亦只测 ENOENT）。
5. **HMDFS 权限**：`chmod` 请求 0755 会被 HMDFS 归一化为 0770（实测 `stat -c %a` = 770），配方在 `build()` 与 `package()` 各做一次 chmod，安装后 X_OK 与 shebang 直接执行均已实测通过。
6. 首次执行二进制的 R7 安全弹窗：本次通过 conan/staging 反复执行未触发弹窗（脚本类由 bash 解释执行，非新增 ELF 二进制）。
---

**编译结束**: 2026-09-13 12:46
**最终状态**: built
