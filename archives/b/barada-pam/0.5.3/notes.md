# barada-pam 0.5.3 适配笔记

## 范围

- 软件：`barada-pam` 0.5.3（赛事任务显示为 `barada-pamC++`）
- 分支：`feat/barada-pam-0.5.3`
- 构建系统：Autotools + C++
- 上游主页：<https://barada.sourceforge.net/>
- 源码来源：Debian main pool 的官方发布归档
- SHA-256：`9054018a6e6a84bea1a460dec61680b3f27fac3136bcda8d1490ee451f25e94a`

## W0 依赖检查

预检命令：

```sh
bash ci/scripts/preflight_check.sh barada-pamC++/0.5.3
```

初始预检在配方生成前通过（无依赖声明）。配方生成后再次通过，以下依赖均已从 `ohpcd` 的 recipe 与 OHOS armv8 二进制解析/下载：

- `boost/1.90.0.4`
- `linux-pam/1.7.2`
- `openssl/3.5.6`

## 上游构建与测试分析

- `configure.ac` 直接检查 Boost Filesystem/System、PAM 和 OpenSSL crypto。
- Boost 1.90 的发布包已将 Boost.System 作为 header-only 组件提供，不再发布
  `libboost_system`；上游 0.5.3 的 `configure.ac`/`configure` 仍强制检查该库。
  配方通过两个 per-file 补丁移除这个过时探测，保留 Boost.Filesystem、PAM 和
  OpenSSL 的真实链接检查。
- `src/Makefile.am` 安装 `barada-add` 到 `bin`，安装 `pam_barada.so` 到 `lib/security`。
- 上游只把 `HexTest` 声明为 `noinst_PROGRAMS`，没有设置 Automake `TESTS`；因此生成的 `make check` 目标会构建 `HexTest`，但不会执行它。
- 配方保留 `make check`，并显式运行 `build-release/src/HexTest`，避免把“只编译未测试”误报为通过。
- 消费者测试在鸿蒙 hishell 上通过 `dlopen` 加载 `pam_barada.so`，查找并调用
  `pam_sm_setcred`，返回预期的 `PAM_CRED_UNAVAIL`；另执行安装后的 `barada-add`，不修改
  `/etc/barada.d`。WSL2 的 qemu 没有 OHOS 动态加载器，早期 WSL 记录中的该分支是跳过项；
  当前已由鸿蒙端原生运行时补齐。

## Conan 配方

- `AutotoolsDeps` 把依赖头文件、库目录和链接库注入 configure/link 检查。
- `AutotoolsToolchain` 使用 `--prefix=/`，配合 Conan 的 `DESTDIR` 安装到包目录。
- 包类型为 `application`；`package_info()` 不伪造 `-lbarada-pam`，仅声明 `bin` 和 `lib/security`，并导出运行时 PATH/LD_LIBRARY_PATH。
- OHOS 包内所有已安装 ELF（`bin/barada-add` 和 `lib/security/pam_barada.so`）均由 `llvm-objcopy` 去除旧签名段后调用 `binary-sign-tool` 自签，并校验 `.codesign` 段、恢复执行权限；缺少工具或签名段时明确失败。
- 适配补丁由 `refresh-patch --auto` 生成：`0001-configure.patch` 同步修改发布
  tarball 自带的 `configure`，`0002-configure.ac.patch` 修改源定义；这样 OHOS
  构建不依赖设备侧重新运行 `autoreconf`。
- `0003-configure-hmdfs.patch` 将发布 `configure` 中创建 Autoconf 临时目录的
  `umask 077` 改为 `umask 022`，避免鸿蒙 HMDFS 下 `config.status` 无法写入
  `subs.awk`；补丁由 `refresh-patch --auto` 生成。
- OHOS 配方构建阶段将 `CONFIG_SHELL`/`SHELL` 固定为设备可用的 `/bin/sh`，避免共享
  profile 指定的 Bash 在 Conan HMDFS build 目录中无法稳定 `getcwd`。

## 验证记录

已完成：

```text
source URL 下载成功，SHA-256 = 9054018a6e6a84bea1a460dec61680b3f27fac3136bcda8d1490ee451f25e94a
ohc-run.py conan-init barada-pam 0.5.3：成功
鸿蒙 `ohc-run.py conan-verify barada-pam 0.5.3 --profile ohos-aarch64-hmfs`：
G1/G2/G3/G4/L2/L4/L5 全部通过。
鸿蒙原生 `conan create`：OHOS arm64 配置、编译、打包和 ELF 签名通过；上游
`make check` 与显式 `HexTest` 运行通过。
鸿蒙原生 `test_package`：`dlopen`/`dlsym(pam_sm_setcred)`、PAM 返回值和安装后的
`barada-add` 均通过，3/3 测试通过。
鸿蒙端 PR 范围 W3：`setup.sh` 与 `build_and_test.sh` 全部通过，并生成
`.ci-result.json`；完整仓库扫描曾被 3 个其他归档的既有 junk 文件拦截，按实际单软件
PR diff 重跑后通过。
```

W3 的完整原始输出保存在鸿蒙端 `reports/w3-local-ci.log`；原生 Conan 创建、测试和签名
日志保存在 `reports/conan-create.log`，专用 profile 的验证结果保存在
`reports/conan-verify-report.md`。

另外，使用 `ohpcd` 依赖头文件和 macOS Homebrew OpenSSL 对上游 `HexTest.cpp + Util.cpp` 做了 host-side 编译/运行；因 macOS 没有 Linux-PAM 可链接库，使用了仅用于该不调用 PAM 日志路径的 `-Wl,-undefined,dynamic_lookup` 探索参数。随机字节↔十六进制往返测试输出 `Comparing... Done.`，这只能作为源码级测试证据，不能替代 OHOS `conan create`。

探索性 macOS configure 使用系统路径时首先报告缺少 `boost-filesystem`；本机没有可用
Boost 编译库。此前 macOS Conan 复现因缺少 profile 指定的
`/data/service/hnp/bin/bash` 退出（错误 126），该结果是本机环境边界，不是源码
编译通过证据。WSL 通过把 `/data/service/hnp/bin`、OHOS SDK 的
`native/llvm/bin` 与 `toolchains/lib` 加入 PATH，使用真实 `binary-sign-tool` 完成了
包签名；完整原始输出保存在 `reports/conan-create.log`。

仍待外部完成：

- W4 独立审计结果需要随最终 PR 证据归档；GitCode push/PR、CI 绿灯和赛事平台提审仍未完成。

在具备 OHOS/WSL 工具链的环境中恢复：

```sh
CONAN_HOME=/path/to/conan-home \
  PATH=/path/to/repo/.venv/bin:$PATH \
  /path/to/repo/.venv/bin/python scripts/ohc-run.py conan-verify barada-pam 0.5.3
```

然后按 `finish → W4 audit → submit` 继续；当前归档状态为 `built`，未上传 Conan
制品，不能标记为 `published`。

### 对话 #1（2026-08-25）

- 在 WSL2 上完成 OHOS arm64 Conan W3：G1/G2/G3/G4/L2/L4/L5 通过，W3 通过。
- WSL 动态运行限制已明确记录；未把 qemu 的静态 CLI 探针宣称为 PAM 模块动态加载
  的设备等价验证。

### 对话 #2（2026-08-26）

- 在 `ssh hm` 鸿蒙 aarch64 hishell 上完成原生 Conan 构建、上游测试、消费者测试和签名，
  补齐了 WSL 无法完成的 PAM 动态加载证据。
