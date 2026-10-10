# kea-admin 3.0.3 适配笔记

## 编译环境

- 目标机：HarmonyOS PC（OpenHarmony aarch64，OHOS musl/libc++，clang）
- Conan 2.29.1，profile：`ci/conan/profiles/ohos-aarch64`
- 依赖：boost/1.85.0、log4cplus/2.2.0.1、openssl/3.5.8.1、gtest/1.17.0.1（tests）、meson/1.11.0（tool）
- 源码：`https://ftp.isc.org/isc/kea/3.0.3/kea-3.0.3.tar.xz`（sha256 09702ddb…4d631）

## 定位与构建模型（关键判断）

kea-admin 是 ISC Kea 的数据库管理工具，源码位于发布包 `src/bin/admin`。与 Kea 其余组件不同，它**不是编译产物**：上游 Meson 目标（`src/bin/admin/meson.build`）没有 `executable()`、没有 `dependencies:`/`link_with:`，唯一构建动作是 `configure_file()`——把 `kea-admin.in` 展开成 `kea-admin` 脚本、`admin-utils.sh.in` 展开成共用助手，并把 mysql（40 个 `upgrade_*.sh` + 3 个基础脚本）与 pgsql（34 + 3）维护脚本物化到构建树。

因此本配方在 Meson 配置阶段（`meson setup`）即停止，**无编译、无链接**。两个连带结论：

1. Kea 是单一 Meson 工程，顶层 `meson.build` 的配置门禁（boost 无 fallback、openssl 为默认 crypto 后端、log4cplus wrap fallback）绕不开，故配方声明这三个工程级依赖——它们只服务配置期探针，不进入交付物，`package_info()` 不向消费者传播。
2. 上游 `meson test` 只重建测试注册中 `depends:` 声明的目标（`--no-rebuild` 即跳过这一步）；本包 admin 套件的注册无 `depends`，相邻 memfile 注册的 `depends:` 行在上游发布包中亦为注释态（补丁 0004 上下文可见），因此 build() 内不触发任何编译——交付物完全来自 configure_file()。脚本包仍然要求工程整体可**配置**（单一 Meson 工程的顶层配置门禁见上条）；memfile 套件需要本工程其它编译目标（kea-dhcp4/kea-dhcp6/kea-lfc），仅在本地验证阶段以显式 `meson compile` 全树构建后执行（见下文「编译步骤」）。

## 补丁（9 枚）

| 补丁 | 目标 | 作用 |
|------|------|------|
| 0001 | 顶层 meson.build | `system()=='harmonyos'` 归一化为 `linux`（否则平台分支直接 error） |
| 0002 | src/bin/admin/kea-admin.in | 运行期自定位（package_root → share/kea/scripts）；upgrade 脚本调用加 `sh` 前缀 |
| 0003 | 顶层 meson.build | 配置期脚本经解释器前缀：cd-and-run.sh / env.sh / grabber.py / config-report.sh |
| 0004 | src/bin/admin/tests/meson.build | 四套 shell 测试注册改为 `sh` + args 形式（admin/memfile/mysql/pgsql） |
| 0005 | admin_tests.sh.in | 17 例中的 kea-admin 调用全部 `sh` 前缀 |
| 0006 | src/lib/testutils/dhcp_test_lib.sh.in | version_test 助手：目标是脚本（`#!`）经 `sh`，ELF 直跑 |
| 0007 | mysql/pgsql scripts meson.build | `datarootdir` 由烘死前缀改为运行期自定位（`$(cd "$(dirname "$0")/../../.." && pwd)`） |
| 0008 | src/lib/process/cfgrpt/meson.build | `mk_cfgrpt.sh` 经 `sh` 调用 |
| 0009 | src/lib/testutils/dhcp_test_lib.sh.in | `wait_for_file`/`wait_for_process_to_stop`：`$(date +%s)` 提出算术展开（ksh93 展开发散） |

平台根因只有两类：(a) Meson 在 OHOS 上报告 `system='harmonyos'`，Kea 白名单不含它；(b) HarmonyOS PC 内核拒绝 shebang 脚本 `execve()`（EACCES/126，**与文件权限无关**——文件 0770、可执行位在、`os.access(X_OK)` 为真，execve 仍被拒），凡是"直接执行脚本"的调用点都要改为解释器前缀。另有重定位改造（0002/0007）：上游把 configure 期绝对前缀（`--prefix=/`）烘进脚本，包内 `/share/kea` 路径不存在，改为按脚本自身位置运行期解析。

## 编译步骤（真机）

```sh
conan create archives/k/kea-admin/3.0.3 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

build() 内：`sh <meson包>/bin/meson setup …`（meson 的 bin/meson 本身是 `#!` 包装脚本，同样经 sh）→ `sh <meson> test -v --timeout-multiplier 4 -C <build> admin_tests.sh`。

memfile 套件（3 例）需要 kea-dhcp4/kea-dhcp6/kea-lfc（本工程其它目标、非本包交付物），不在配方 build() 内执行；本地验证阶段全树构建后执行（HMDFS 无符号链接，先补齐构建树 SONAME 文件，见问题表；`--no-rebuild` 使测试阶段只运行、不做任何重建）。全树构建的源树 = 3.0.3 发布包应用配方 9 枚补丁（apply_patches.py，patch_ng）后，再叠加 kea-hook 家族同源的两枚 src/lib/dhcp 编译适配补丁（0002-src-lib-dhcp-iface_mgr_linux.cc、0005-src-lib-dhcp-iface_mgr_linux-getifaddrs-fallback——仅本地验证构建使用，不属于本包交付补丁集）：

```sh
sh <meson> compile -C <builddir> -j 6 kea-dhcp4 kea-dhcp6 kea-lfc   # 414 个目标；-j 6 限并发
sh ka_libfix.sh <builddir>   # 复制 libkea-*.so.<maj>.<min>.<patch> → libkea-*.so.<maj>
cd <builddir> && . ./conan/conanrun.sh
sh <meson> test -v --no-rebuild --timeout-multiplier 10 -C <builddir> memfile_tests.sh
```

## 遇到的问题与解决方案

| 问题 | 现象 | 解决 |
|------|------|------|
| Meson 不识别 harmonyos | `meson setup` 在平台分支直接 error | 补丁 0001 归一化为 linux |
| 脚本 execve 被内核拒绝 | 任何 `#!/…` 文件直接执行 EACCES/RC 126；`sh 脚本` 正常 | 全部调用点解释器前缀（0002/0003/0004/0005/0006/0008）；配方 meson 包装脚本经 sh |
| 包内绝对路径不存在 | 上游烘死 `--prefix=/`，脚本引用 `/share/kea` | 0002/0007 运行期自定位 |
| boost 1.90/1.91 缺头文件 | Kea `required:true` 探测 boost/interprocess、circular_buffer 等失败 | 锁 boost/1.85.0 |
| pthread_setcancelstate 未声明 | OHOS musl `pthread.h` 缺声明，boost sp_thread_sleep.hpp 编译失败 | `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 配置探针缺共享库 | cpp.run() 探针真实执行，host 依赖不可见 | 生成期把依赖 libdir 注入 LD_LIBRARY_PATH（conanbuildenv） |
| CI PATH 无 llvm-ar/llvm-ranlib | meson 静态链接器探测失败 | 从 `tools.build:compiler_executables` 推导 bin 目录注入 |
| 单测 30 s 预算截断 | admin 17 例每例一个进程，真机 85.68 s | `--timeout-multiplier 4`（配方内）/`10`（memfile 本地） |
| 官方 conan-verify L2 崩溃 | L2 冒烟直接 execve `bin/*`，脚本包 PermissionError 穿透（`_run` 只捕 Timeout/NotFound），验证整体崩溃且不留报告（`l2_probe.py` 复现） | 平台惯例脚本工具经 `sh` 前缀调用（E087、cdb 先例）；本次以 sh-proxy 驱动官方 runner（只把 `/.conan2/p/` 下 `#!` 文件改经 sh，其余逻辑零改动），L2 经代理通过 |
| 裸 `sh` ENOENT | CPython subprocess 走 posix_spawn 不查 PATH | 消费者测试 `shutil.which("sh")` 解析绝对路径 |
| ksh93 算术展开翻倍命令名 | `/system/bin/sh` 为 ksh93 语义，`$(( $(cmd) + n ))` 把命令名翻倍（`date`→`datedate`，展开按空值计算）；memfile.init 的等待 helper deadline 退化为纯 timeout，报 "kea-dhcp4.csv was not created in time" | 补丁 0009：`now=$(date +%s); deadline=$((now + timeout))`；全树扫描仅 2 处命中，其余 `$((...))`（纯算术/无嵌套命令替换）不受影响 |
| 构建树 SONAME 文件缺失（HMDFS 无符号链接） | memfile 套件所用的 kea-dhcp4/kea-dhcp6/kea-lfc 启动即报 `Error loading shared library libkea-*.so.<major>` / relocation error——meson 构建树中只有 `libkea-*.so.<major>.<minor>.<patch>` 实体文件，SONAME 名文件（meson 通常以符号链接提供）在 HMDFS 上无法生成 | 本地验证环境预置：把全部 `libkea-*.so.<major>.<minor>.<patch>` 复制为 `libkea-*.so.<major>`（`ka_libfix.sh`）。仅影响"从构建树运行 Kea 服务端"这一本地验证场景；kea-admin 交付物为纯脚本包、不含 Kea 共享库，不受影响 |

## 真机验证

- 官方 conan-verify（8 门禁 G0–G4 + L2/L4/L5）：Verdict PASS（2026-10-04T10:45:58，干净重建 rrev 801d00e89c97）。G0 PASS（命中 E490 警告：autotools 脚本文案，本包 meson 构建不受影响）、G1 PASS、G2 PASS（conan create 干净构建）、G3 PASS、G4 PASS（bin/ 1 个文件；驱动侧转置补丁使官方 runner 在 conan 2.29.1 下正确解析包 ID）、L2 PASS（`kea-admin: 3.0.3`，冒烟门禁经 sh 前缀实际执行）、L4 PASS（0 个 ELF）、L5 PASS（首次基线 85 个文件）；报告 `reports/conan-verify-report.md`，全绿标记 `.conan-verified`。
- 上游测试：admin_tests.sh 17/17（meson 1/1 OK，85.68 s，--timeout-multiplier 4；随 G2 干净构建实跑）；memfile_tests.sh 3/3（memfile.version/init/upgrade 全 OK，12.71 s，--timeout-multiplier 10；需先按 HMDFS 特性补齐构建树 SONAME 文件，见问题表）。
- 消费者契约测试 test_package/test_kea_admin.py：45/45 全部通过（TEST SUMMARY: 45 passed, 0 failed, 45 total / TEST RESULT: SUCCESS；随 G2 干净构建实跑）——覆盖产物清单（bin/kea-admin shebang/可执行位、admin-utils.sh、mysql 40+3、pgsql 34+3、licenses）、重定位（运行期解析、无 configure 残留绝对路径、upgrade 调用 sh 前缀、admin-utils 可 source）、版本/用法（-v/--version/-V/--help 与默认脚本目录回显）、10 条错误路径 + memfile stats-recount、mysql/pgsql 全链路（以编译出的 C 桩替换 mysql/psql 客户端：argv 透传、schema 字节数送达、40 条 Processing、≥40 次 schema_version 查询）、2 项负向控制（缺 admin-utils、缺 schema 脚本）。

## 已知限制

- mysql/pgsql 上游测试套件未注册（后端 disabled，与上游注册条件一致）；消费者测试以 C 桩驱动客户端调用面，不依赖真实数据库。
- `lease-dump` / `lease-upload` 需要 `kea-lfc`（属 Kea 工程其它目标，不在本包内）：补丁 0002 将 `KEA_LFC` 的默认路径由 configure 期系统路径（`@sbindir@/kea-lfc`）改为包内 `<package>/bin/kea-lfc`，使用时须把 kea-lfc 放入该目录（本包自包含布局的连带结果）。
- `bin/kea-admin` 的受支持运行形态是 `sh <package>/bin/kea-admin`（平台内核限制）；文件保留上游的 0755 权限位。
