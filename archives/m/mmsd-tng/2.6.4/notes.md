# mmsd-tng 2.6.4 OHOS（HarmonyOS PC aarch64）适配笔记

- 目标库：mmsd-tng 2.6.4（任务书：`feat/mmsd-tng-2.6.4`）
- 上游：https://gitlab.com/kop316/mmsd ，tag 2.6.4 → commit `f860df588bcf0e4c0ed06f5bca848bf5624ec292`（2025-07-04）
- 源码 sha256：`111eba8489f0b8143ad5143124f31bf2f8c4a52d975adf4df99230708a9edd2d`（123761 B，GitLab tag 归档 = Debian orig，逐字节一致）
- 语言：C 主体（`src/*.c`）+ 1 个 C++ 文件 `src/phone-utils.cpp`（c/cpp 族，R47 lang-preflight 通过）
- 构建系统：meson（`meson.build:5` `>= 0.56.0`，默认后端 ninja）
- 产物（package_type = application）：
  - `bin/mmsdtng`（MMS 守护进程，`install:true`）
  - `bin/mmsctl`（D-Bus 控制工具，仅 `-Dbuild-mmsctl=true` 时构建，`install:true`）
  - 构建期工具 `tools/decode-mms`、`tools/create-hex-array`（上游未 install，不入包）
  - 内部静态库 `libmms.a` / `libplugins.a`（上游未 install，不入包；本库无对外 .so/.a）

---

## 1. 依赖（W0 已核验：27/27 可消费，GAP_N=0，见 ../mmsd-tng-2.6.4-deps/）

| 依赖 | 版本 | 来源（上游 file:line） |
|---|---|---|
| glib | 2.84.0.1.1 | `meson.build:117 glib-2.0>=2.16`（含 gio-2.0）、118 mm-glib |
| libmm | 1.24.2 | `meson.build:118 mm-glib>=1.14` |
| libsoup3 | 3.6.5-r3 | `meson.build:119 libsoup-3.0` |
| c-ares | 1.34.6 | `meson.build:120 libcares>=1.18.1` |
| libphonenumber | 8.13.51 | `meson.build:122 phonenumber required:true` |
| mobile-broadband-provider-info | 20240407 | `meson.build:31`（无条件，取 `database` 变量） |
| dbus / json-c | 1.14.10 / 0.18 | `tools/meson.build:18,19`（仅 `build-mmsctl=true`） |
| meson / ninja | 1.11.0 / 1.12.1 | 构建系统（本机与 CI 均无系统 meson，用 tool_requires） |

**zlib override**：`libmm → glib2/2.88.0` 钉住 `zlib/1.3.1`，与 `glib/2.84.0.1.1` 的
`zlib/1.3.1.1` 在图里冲突（`Version conflict: Conflict between zlib/1.3.1 and
zlib/1.3.1.1 ... originates from glib2/2.88.0`）。统一到已发布的 **PIC 变体
`zlib/1.3.1.1`**（`self.requires("zlib/1.3.1.1", override=True)`），做法与
`libsoup3/3.6.5-r1` 相同（该配方注释明确说明这是为对抗 glib2/2.88.0 的 zlib 钉版）。

---

## 2. 适配过程中的真实错误、根因与修复（按发生顺序）

### E1（真实首错） clang 不认「case 标签后紧跟声明」

**首次真实错误**（`meson compile`）：

```
../builds/mmsd-tng-2.6.4.work/meson.build:1:0: ERROR: Unknown compiler(s): [['clang']]
The following exception(s) were encountered:
Running `clang --version` gave "[Errno 2] No such file or directory: 'clang'"
```

> 说明：本机 `clang` 明明存在（`/data/service/hnp/bin/clang`，直接执行 exit=0）。
> 根因是 **OHOS libc 的 `posix_spawn` 不按 PATH 解析裸命令名**：环境里 `CC=clang`，
> meson 原样拿去 Popen → ENOENT。Python 侧复现：
> `shutil.which("clang")` 命中，而 `subprocess.run(["clang","--version"])` 抛 `FileNotFoundError`。
> **修复**：`CC/CXX/AR/AS/STRIP/NM/RANLIB` 与 meson `[binaries]` 全部改为绝对路径
> （`generate()` 里 `shutil.which()` 解析）。修复后 meson 正常识别
> `C compiler for the host machine: /data/service/hnp/bin/clang (clang 15.0.4)`。

### E2 `mobile-broadband-provider-info` 缺 `database` 变量

```
../builds/mmsd-tng-2.6.4.work/meson.build:31:87: ERROR: Could not get pkg-config variable
and no default provided for <PkgConfigDependency mobile-broadband-provider-info: True []>
```

**根因**：PkgConfigDeps 生成的 `mobile-broadband-provider-info.pc` 只有 prefix/Name/Version，
没有 `database=` 变量；上游 `meson.build:31` 需要
`dependency('mobile-broadband-provider-info').get_variable(pkgconfig: 'database')`。
依赖包自带 `share/pkgconfig/mobile-broadband-provider-info.pc` 才有
`database=${pkgdatadir}/serviceproviders.xml`。

**修复**：`generate()` 把依赖包的 `share/pkgconfig` 前置进 `pkg_config_path`。

### E3 clang 拒绝 case 标签后声明（首编译真错）

```
../builds/mmsd-tng-2.6.4.work/src/service.c:3966:7: error: expected expression
      gsize length;
../builds/mmsd-tng-2.6.4.work/src/service.c:4016:6: error: cannot jump from switch statement to this case label
     default:
../builds/mmsd-tng-2.6.4.work/src/service.c:3967:25: note: jump bypasses initialization of variable with __attribute__((cleanup))
```

**根因**：`src/service.c` 的 `process_request()` 中
`case MMS_REQUEST_TYPE_POST_TMP:` 后直接写声明（`gsize length;` /
`g_autofree gchar *contents;` …）。ISO C 规定标签只能标记语句，声明不是语句；
GCC 以 GNU 扩展容忍（Debian 用 gcc 构建，故上游无感），**clang 直接报错**。
第二处报错同理：`g_autofree` 带 `__attribute__((cleanup))`，跳到后面的 `default:`
会绕过其初始化，clang 亦判定为错误。

**修复**（`patches/0002-src-service.c.patch`，+2 行）：给该 case 分支加一层块作用域

```diff
     case MMS_REQUEST_TYPE_POST:
     case MMS_REQUEST_TYPE_POST_TMP:
       /* Collect contents of file to POST */
+      {
       gsize length;
       ...
       return msg;
+      }
      default:
```

语义不变（变量本就只在该分支内使用）。**扫描确认全库仅此一处**（脚本检测
`case/default` 标签后紧跟声明：`src/*.c`、`src/*.cpp` 中真实候选数 = 0（修复后））。

### E4 找不到 `phonenumbers/logger.h` / 静态库传递依赖缺失

```
../builds/mmsd-tng-2.6.4.work/src/phone-utils.cpp:27:10: fatal error: 'phonenumbers/logger.h' file not found
```

**根因**：上游用 `cc.find_library('phonenumber', required: true)` —— 只产出
`-lphonenumber`，没有 include 目录。而 conan 的 libphonenumber/8.13.51 是**静态库**
（`libphonenumber.a` + `libgeocoding.a`），静态链接还需要 protobuf/abseil/icu 的 libs，
`find_library` 完全拿不到。

**修复**（`patches/0001`、`patches/0003`）：`meson.build` 与 `unit/meson.build` 改用
`dependency('libphonenumber', required: true)` —— 依赖包自带的上游风格
`libphonenumber.pc` 提供 `Cflags`（include 目录）与
`Libs: -L… -lgeocoding -lphonenumber -lpthread` +
`Requires: protobuf abseil-cpp icu4c googletest`。

### E5 `unit/test_service_providers` 链接缺 gio 符号

```
ld.lld: error: undefined symbol: g_file_new_for_path
ld.lld: error: undefined symbol: g_io_error_quark
```

**根因**：`unit/meson.build` 的 `test_dependencies` 只声明 `glib-2.0`、`mm-glib` …
而 `test-service-providers.c` 用 gio API。上游在 Debian 上不炸，是因为 Debian 的
`mm-glib.pc` 带 `Requires: gio-unix-2.0, glib-2.0, gio-2.0, gobject-2.0`，gio 由
mm-glib 传递进来；而 **conan 的 libmm 未在 package_info 里声明 gio/gobject，
PkgConfigDeps 生成的 `mm-glib.pc` 只有 `Requires: glib-2.0 dbus`**。

**修复**：`generate()` 生成对齐上游的 `mm-glib.pc`
（`Requires: glib-2.0 gio-2.0 gobject-2.0 dbus-1`）放入 pc-fix 目录并前置。

### E6 abseil 要求 C++17，meson 默认 gnu++14

```
absl/base/policy_checks.h:81:2: error: "C++ versions less than C++17 are not supported."
absl/meta/type_traits.h:126:12: error: no member named 'conjunction' in namespace 'std'
```

**根因**：`meson.build` 未声明 C++ 标准；meson 无 cpp_std 时 clang 15 默认 gnu++14，
而 libphonenumber 经 abseil 头文件要求 ≥C++17（Debian 上 gcc 默认 gnu++17 故无感）。

**修复**：profile 的 `compiler.cppstd=17` 由 MesonToolchain 自动映射为 `cpp_std=c++17`；
`generate()` 里再兜底（`tc.cpp_std` 为空时显式设 `c++17`）。

### E7 protobuf 静态库缺 `libutf8_validity` / `libutf8_range`

```
ld.lld: error: undefined symbol: utf8_range_IsValid
>>> referenced by parse_context.cc ... in archive /…/p/proto…/lib/libprotobuf.a
ld.lld: error: undefined symbol: utf8_range_ValidPrefix
```

**根因**：conan protobuf/33.6 包内**有** `libutf8_validity.a` / `libutf8_range.a`，
但 `package_info()` 只写了 `cpp_info.libs = ["protobuf"]`，PkgConfigDeps 生成的
`protobuf.pc` 因而缺这两个库（protobuf ≥33 的 `parse_context.cc` 引用它们）。

**修复**：`generate()` 生成补全的 `protobuf.pc`
（`Libs: … -lprotobuf -lutf8_validity -lutf8_range -lpthread`，顺序在 `-lprotobuf` 之后）。

### E8 conan 包内可执行文件被内核拒绝执行（EPERM）

**首次真实错误**（`conan create` → test_package）：

```
[PASS] case1 ...? -> 首次为：
PermissionError: [Errno 1] Operation not permitted:
    '/…/p/b/mmsd-f6e50faba39c4/p/bin/mmsdtng'
```

**根因**：由 `meson install` 直接落地到 conan 包目录的可执行文件在本机被内核拒绝
exec（`Operation not permitted`）。实测排除项：`chmod 770` / `chmod 755` 均无效；
**用构建目录同名产物覆盖后 md5 完全一致却能正常运行** → 与文件内容无关，属该安装
路径/inode 上的安全或属性标记问题（与 account-utils 1.4.0 配方记录的 meson install
落地坑同类）。

**修复**（`package()`，+7 行）：在 `meson.install()` 之后，从构建目录把
`mmsdtng`、`mmsctl` 重新 `copy()` 到 `package_folder/bin`（新建 inode）。修复后
`conan create` **exit=0**，包内两个可执行文件均可直接运行。

### 修复后结果（conan create 全绿）

```
meson compile exit=0
[33/35] Linking static target src/libmms.a
[34/35] Linking target tools/decode-mms
[35/35] Linking target mmsdtng
```

产物（`file`）：`mmsdtng: ELF 64-bit LSB shared object, ARM aarch64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped`

运行验证（conanrun 环境）：
`mmsdtng --version` → `2.6.4, git version: 2.6.4`（exit 0）；`decode-mms`、`mmsctl` 均可执行。

---

## 3. 上游测试（实跑，非推断）

入口：`unit/meson.build:9-37` 注册 4 个 meson test（workdir = 项目根）。

```
$ meson test -C <builddir> --print-errorlogs
1/4 mmsdtng:test wsp               OK              0.23s
2/4 mmsdtng:test mms               OK              0.25s
3/4 mmsdtng:test phone utils       OK              0.24s
4/4 mmsdtng:test service providers OK              0.06s

Ok: 4   Fail: 0   Skip: 0
```

上游测试用例数据（`unit/*.mms` 16 个 + `test-service-providers.xml`）由 `test mms` /
`test service providers` 用例读取，全部通过。

上游 `test/` 目录是 **shell/python 脚本**（`#!/usr/bin/python`，走 mmsctl + D-Bus），
不是 meson 注册的自动化测试，且依赖运行中的 mmsd-tng 守护进程与 D-Bus session bus
（本机无 `DBUS_SESSION_BUS_ADDRESS`）——因此不作为构建期用例执行，属运行期集成测试入口。

`build()` 内通过 `Meson.test()` 执行上述 4 个上游用例，CI 同样会跑（可被
`tools.build:skip_test` 关闭）。

---

## 4. 构型与开关

- `build_mmsctl`（默认 **true**）：上游 `meson_options.txt:1` 默认 false，但上游 CI
  （`.gitlab-ci.yml`：`meson -Dbuild-mmsctl=true -Dwerror=true _build`）与 Debian
  (`debian/rules`: `dh_auto_configure -- -Dbuild-mmsctl=true`) 都用 true，且它是本包唯一的
  用户可见 CLI（`mmsctl`），故本配方默认 true；两套构型的依赖（dbus/json-c）均实测可消费。
- 不 strip：`generate()` 保持 meson 默认（不 strip）。OHOS loader 校验链接期写入的
  `.codesign` 段哈希，strip 会使其失配（libsoup3/telemetry 同结论）。
- R26 不适用：本库不安装任何与系统同名的 `.so`/`.a`（只有可执行文件入包）。

## 5. 遗留与风险

- 运行期 `mmsdtng` 首次启动会在 `$HOME/.mms/<plugin>/mms` 写配置，并需要
  `mobile-broadband-provider-info` 的 `serviceproviders.xml`（本包通过 `Requires`
  传递，运行期由依赖包提供）与 ModemManager 服务；这些属运行期 OS 集成，不在构建期测试范围。
- `meson test` 在 CI 上依赖依赖包的运行期共享库路径（conan runenv），已在
  `build()` 中由 conan 注入。
---

## 6. 最终门禁结果（本地，提交前停止）

| 门禁 | 命令 | 退出码 | 结果 |
|---|---|---|---|
| conan create | `conan create archives/m/mmsd-tng/2.6.4 -pr:h/-pr:b=ohos-aarch64 '--build=mmsd-tng/*'` | **0** | build() 内上游测试 `Ok: 4 / Fail: 0`；test_package **4/4 PASS**；`Package created` |
| conan-verify | `ohc-run.py conan-verify mmsd-tng 2.6.4` | **0** | G0/G1/G2/G3/G4 + L2/L4/L5 PASS |
| finish (W2) | `ohc-run.py finish mmsd-tng 2.6.4 built` → Step 9/10 | — | 通过（无框架文件混入） |
| finish (W3，阻塞门禁) | Step 5/10 → `ci/conan/{setup.sh,build_and_test.sh}` | **0** | **W3 本地 CI 模拟通过**（`reports/w3-local-ci.log`），`.ci-result.json` exit_code=0 |
| 上游测试 | `meson test -C <builddir> --print-errorlogs` | **0** | 4/4 OK（test mms / wsp / phone utils / service providers），0 Fail 0 Skip |
| Staging 验证 | `conan install --requires=mmsd-tng/2.6.4@ohpcd/stable … --deployer=full_deploy` + 实跑 | **0** | `.staging-verified`；`reports/staging-verify.log` |
| JC（PR 文件集） | `JUNK_PR_DIFF=pr.diff bash ci/scripts/junk_check.sh` | **0** | `JC_RESULT=pass JC_ERRORS=0`（含 JC6 单软件原子性），`reports/junk-check-prdiff.log` |

**W3 首轮失败说明**：本地首次 W3 在 junk_check 的 **full 模式**命中 4 个文件，全部是
基线提交 `32018bae04`（`!10724 merge feat/liblqr-0.4.3 into main`）里**其它包的存量**：
`archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、
`archives/k/kics/2.1.20/.staging-verified`、`archives/t/thc/3.8/.staging-verified`。
`junk_check.sh` 的正确判据是 **prdiff 模式**（脚本注释："pr.diff 是 PR 文件清单的唯一
权威来源"）；本分支按规程尚未提交，`git diff origin/main...HEAD` 为空 → 回退 full
整仓扫描才误报。用本包 12 个变更文件生成 `pr.diff` 复核：**pass**（证据见
`reports/pr.diff` 与 `reports/junk-check-prdiff.log`；该 `pr.diff` 已从仓库根目录移除）。

**未决（非阻塞）**：finish Step 7（W5 知识图谱，脚本标注"非阻塞"）报 `unreferenced=9`
—— `manifest.yaml` 的 9 条 `knowledge_gained` 尚未沉淀为知识图谱条目。本阶段按任务
约束"只处理目标库自身文件"，未执行 `graph add --draft`；如需按【知识库扩展】提交，
可在 PR 阶段补 2–4 条草稿（clang case 标签 / OHOS posix_spawn 裸命令名 / conan 包 .pc
缺口 / meson install EPERM）并回填 `knowledge_ref`。

**未执行（按要求停止）**：未 commit、未 push、未创建 Issue/PR、未上传 Conan 制品、未做远端 Review。
---

## 7. 知识沉淀（草稿）与 PR 交付范围

本包随 PR 提交 **5 条知识草稿（kv + md 一一对应）**，均落在 `knowledge/drafts/`：

| # | 草稿（id / 文件前缀 `mmsd-tng-2.6.4-`） | 对应本包证据 |
|---|---|---|
| 1 | `clang-case-label-followed-by-declaration` | §2/E3（`src/service.c` case 后声明；`patches/0002`） |
| 2 | `ohos-posix-spawn-bare-command-name` | §2/E1（`CC=clang` → meson Unknown compiler；`generate()` 绝对路径） |
| 3 | `conan-dep-pkgconfig-metadata-gaps` | §2/E2/E4/E5/E7（mbpi `database` / dbus-1 别名 / mm-glib 丢 gio / protobuf utf8 库） |
| 4 | `meson-install-executable-eperm` | §2/E8（`package()` 从 build 目录重复制） |
| 5 | `clang-default-cppstd-below-gcc` | §2/E6（abseil 需 C++17；`cpp_std` 兜底） |

同时把版本级 `manifest.yaml` 的 9 条 `knowledge_gained` 逐条回填 `# knowledge_ref: <草稿 id>`
（映射：1→草稿1；2→草稿2；3/4/5/6/7→草稿3；8→草稿5；9→草稿4）。
回填后 W5 的 `check_knowledge_gap` 报告 `knowledge_count=9 unreferenced=0` → `✅ 知识完整性检查通过`。

> 说明：`finish` Step 7 仍会打印一条 ❌，其 `issues=1` 来自**正式图谱存量条目**
> `E219/E253/E305` 的 `root_cause`/`rec_approach` 为空（非本包、非本次改动），
> 以及仓库级 2174 条历史草稿待审；两者均为既有状态，脚本本身标注该步"非阻塞"。

**PR 交付文件白名单（22 个）** —— 提交必须按此逐路径 `git add`：

```
archives/m/mmsd-tng/README.md
archives/m/mmsd-tng/commands.json
archives/m/mmsd-tng/2.6.4/{conanfile.py,conandata.yml,manifest.yaml,notes.md}
archives/m/mmsd-tng/2.6.4/patches/{0001-meson.build.patch,0002-src-service.c.patch,0003-unit-meson.build.patch}
archives/m/mmsd-tng/2.6.4/test_package/{conanfile.py,test_mmsd_tng.py,MANIFEST.yml}
knowledge/drafts/mmsd-tng-2.6.4-{clang-case-label-followed-by-declaration,clang-default-cppstd-below-gcc,
  conan-dep-pkgconfig-metadata-gaps,meson-install-executable-eperm,ohos-posix-spawn-bare-command-name}.{kv,md}
```

⚠️ **禁止 `git add -A` / `git add archives/`**：本工作树存在**非本任务的**外部未提交改动
（`archives/l/libXext/{README.md,manifest.yaml}`，跨全部工作树同 sha256），
误加入会触发 CI JC6 单软件原子性失败。
---

**编译结束**: 2026-09-29 08:23
**最终状态**: built
