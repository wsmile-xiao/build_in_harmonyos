# argc 1.24.0 适配笔记

## 编译环境
- 构建系统: cargo (Rust)
- 编译日期: 2026-08-11
- 编译器: clang/clang++（Rust 工具链经 Harmonybrew bottle 引导安装，martin/1.13.0 先例）
- 状态: built（真机预检通过后由 HMBS 更新为 published）

## 编译步骤

argc 是 Rust 编写的 bash CLI 框架 / 命令运行器，无 configure 步骤：

```bash
# 工具链：先探测设备上已有的 cargo（HNP 工具链 / harmonybrew / rustup），
# 探测不到时用 urllib 直接下载 Harmonybrew OHOS Rust bottle 并解包（不依赖 curl/zsh）
cargo build --release --bin argc   # 构建 bin/argc（build() 阶段）
cargo test --release               # 上游测试套件（必需，test_package 阶段执行）
```

配方要点：
- `source()`：`get()` 下载 GitHub tag 归档 v1.24.0.tar.gz（conandata.yml 为
  gh-proxy.com 镜像 + 官方 URL 的有序列表）并 strip_root
- `generate()`：写 `.cargo/config.toml`——clang 链接器 + rsproxy.cn sparse 镜像
  （设备无 crates.io CA bundle，直达 crates.io 会 TLS 失败）
- `build()`：`_ensure_cargo()` 探测/引导 cargo → `cargo build --release --bin argc`，
  仅构建产物；上游测试不在 build() 运行（hmbs 只采集 test_package 阶段标记，
  且包缓存命中时 build() 会被跳过）
- `package()`：拷贝 target/release/argc 到 bin/
- `package_info()`：`cpp_info.bindirs = ["bin"]`
- test_package/conanfile.py `test()`：`/bin/sh test.sh`（3 消费者用例，
  输出 HMBS_TEST_PACKAGE_RESULT）→ 镜像 cargo 引导 + 重新下载上游 tarball →
  `cargo test --release`，解析 "test result:" 行，`print()` 输出
  HMBS_UPSTREAM_TEST_RESULT 标记

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 预检沙盒中 cargo/rustc 不在 PATH | hmbs 只注入 cmake/make/ninja/python3 | 先探测已知位置（HNP/harmonybrew/rustup/usr/local），无则引导 |
| 2 | `curl -fsSL harmonybrew install.sh` 报 SSL 证书校验失败 | 设备 curl 无 CA bundle，无法验证 https 证书 | 放弃 curl/zsh 安装路径，改用 Python urllib 直接下载 Harmonybrew OHOS bottle（martin/1.13.0 先例） |
| 3 | `brew install rust` 报 "brew: inaccessible or not found" | install.sh 未下载成功，brew 根本不存在 | 见 #2：改为 urllib 下载 rust-1.97.1.arm64_ohos bottle 并解包，用 cargo.real |
| 4 | cargo.real 动态链接 libssl/libcrypto/libz 找不到 | OHOS loader 忽略 DT_RUNPATH | 一并下载 openssl@3 / zlib-ng-compat bottle，把 lib 目录加入 LD_LIBRARY_PATH |
| 5 | cargo 拉取 crates.io 依赖 TLS 失败 | 设备无 CA bundle / 直连不稳 | `.cargo/config.toml` 将 crates-io 替换为 rsproxy.cn sparse 镜像；存在系统 CA 时设 SSL_CERT_FILE |
| 6 | OHOS /tmp 只读 | 平台限制 | TMPDIR/TMP/TEMP 指向 HMBS 注入的 TMPDIR（build 与 test_package 均 cd 到 TMPDIR） |
| 7 | cargo build 链接期找不到 cc | OHOS 无 cc 符号链接 | 设置 CC/CXX=clang/clang++ 与 RUSTFLAGS="-C linker=clang"，.cargo/config.toml 指定 linker |
| 8 | 上游测试计数必须来自真机 | hmbs 硬门禁要求框架输出为唯一依据 | cargo test --release 用 subprocess.run 捕获 stdout/stderr，正则解析真实 "test result: ok. N passed; M failed; K ignored" 行 |
| 9 | bash 不在默认 PATH（测试脚本与 argc 生成的脚本需要） | OHOS 精简 PATH | 将 /data/service/hnp/bin 前置到 PATH |
| 10 | 源码下载 github.com 直连 SSL/超时 | 设备 curl 无 CA bundle | conandata.yml url 改为有序列表：gh-proxy.com 镜像在前，官方 URL 兜底（与 ci/conan/build_and_test.sh GitHub 映射一致），sha256 不变 |
| 11 | bootstrap 下载 bottle 报 `SSL: CERTIFICATE_VERIFY_FAILED` | 设备 Python 无默认 CA bundle，且 `_ensure_cargo()`（内含下载）在 `_build_env()` 设置 SSL_CERT_FILE 之前执行 | 新增 `_download_bottle()`：下载前先探测系统 CA 存储（usr/local/ssl/cert.pem 等，astra/boolector 真机已验证）设置 SSL_CERT_FILE；确实无 CA 时仅对固定内部 harmonybrew 镜像回退非验证上下文（E185/kosli-cli 先例） |
| 12 | cargo 拉取 crate 报 `transfer too slow: failed to transfer more than 10 bytes in 30s`（smawk/0.3.2 下载失败） | rsproxy.cn 镜像可达但存在单文件慢速卡顿，cargo 默认低速阈值（30s/10B）与重试次数（3）过严，慢速抖动被误判为失败 | `.cargo/config.toml` 增加 `[net] retry = 10`、`[http] timeout = 600`、`[http] low-speed-limit = 1`，放宽网络容错；镜像仍用真机验证可达的 rsproxy.cn sparse |
| 13 | test_package 三个用例全挂：`argc --version`/`--help` 报 "Argcfile not found, try \`argc --argc-help\` for help."，第三个用例在 `set -e` 下静默中断 | argc 自身 CLI 只识别 `--argc-*` 前缀标志（--argc-help/--argc-version/--argc-eval...）；裸 `--version`/`--help` 是脚本级标志，无 Argcfile 时会进入 Argcfile 查找分支报错；第三个用例 `argc test_argc_demo.sh hello --name world` 无 Argcfile 直接退出码非 0 | test.sh 改用 argc 真实 CLI：`argc --argc-version`（输出 "argc 1.24.0"）、`argc --argc-help`（含 USAGE 段）；注解脚本改由 `bash test_argc_demo.sh hello --name world` 运行（argc 脚本即普通 bash 脚本，脚本内 `eval "$(argc --argc-eval "$0" "$@")"` 完成解析分发），并捕获退出码避免 set -e 静默中断 |
| 14 | 用例 3 失败：`[fail] script option parsing rc=0 output: shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported` + hello,world | HMBS 平台诊断 shell_getcwd：HNP bash 在 HMFS/HMDFS 工作目录启动时 getcwd 失败（ENOTSUP），在 stderr 打印无害的 `shell-init:` 警告；用例 3 用 bash 运行 argc 注解脚本，`2>&1` 捕获把该行混入输出，与期望 "hello,world" 比对失败（rc 实际为 0） | ① harness 改用 HMBS 注入的 /bin/sh（CONFIG_SHELL/SHELL）执行，不硬编码 /data/service/hnp/bin/bash（conanfile.py 兜底改为 "sh"）；② 用例 3 比对前用 `sed '/^shell-init:/d'` 剥离 bash 启动环境产物行（非脚本输出），断言仍为 rc==0 且输出精确等于 "hello,world"；③ test.sh shebang 改为 /bin/sh，marker command 改为 "/bin/sh test.sh" |
| 15 | 真机预检 incomplete「缺少 HMBS_UPSTREAM_TEST_RESULT 上游测试证据，发现 0 执行 0」；日志显示 `argc/1.24.0: Already installed!` | 双重根因：① 包二进制已在 conan 缓存，conan create 直接复用缓存跳过 `build()`，`cargo test` 从未运行；② 即便运行，hmbs 预检**只从 test_package 阶段 stdout 采集** HMBS_UPSTREAM_TEST_RESULT 标记（tlsx/1.2.2 第 11 轮先例），`build()` 里 `self.output.info()` 输出不被当作上游测试证据 | 上游测试迁到 test_package 阶段：conanfile.py `build()` 仅保留 `cargo build --release --bin argc`（删除 cargo test 块）；test_package/conanfile.py `test()` 镜像 cargo 引导（探测已知位置→Harmonybrew bottle urllib 引导）、重新下载上游 tarball（conandata.yml 同 URL 列表+sha256）、写 `.cargo/config.toml`（clang linker + rsproxy + 网络容错），运行 `cargo test --release` 并用 `print()` 输出 HMBS_UPSTREAM_TEST_RESULT（数字解析自真实 "test result:" 行，discovered==executed 对账一致）；MANIFEST.yml `upstream_test_in_build: false` |
| 16 | 上游测试 rc=127：`.../rust-toolchain/rust/1.97.1/bin/cargo[3]: /storage/Users/currentUser/.harmonybrew/Cellar/rust/1.97.1/bin/cargo.real: inaccessible or not found` | Harmonybrew rust bottle 的 `bin/cargo` 是硬编码 Cellar 绝对路径（`/storage/Users/currentUser/.harmonybrew/Cellar/rust/1.97.1/bin/cargo.real`）的 sh wrapper 脚本；bottle 解包到 build 目录后该路径不存在。主配方 `_ensure_cargo()` 把工具链 bin 目录前置进 `os.environ["PATH"]`，`conan create` 同进程执行 test_package 时 `shutil.which("cargo")` 命中该 wrapper（build() 直接用 `cargo.real` 所以构建成功，test_package 却执行了 wrapper → rc=127） | 双层修复（conanfile.py 与 test_package/conanfile.py 同步）：① `_bootstrap_rust_toolchain()` 解包后重写 wrapper——对 bin 目录中每个带 `.real` 同级且为 `#!` 脚本的普通文件（跳过符号链接/真实 ELF），重写为 `exec "<本地 .real 绝对路径>" "$@"`（open("w") 保留原权限位）；② `_find_cargo()` 命中候选时优先使用其 `.real` 同级二进制，绝不执行 Cellar 路径 wrapper |
| 17 | 上游测试 115/219 失败：insta 快照全部失配，差异仅为两行 bash 启动警告 `shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported` 与 `job-working-directory: ...` | HMBS 平台诊断 shell_getcwd：HNP bash 在 HMFS/HMDFS 工作目录（conan build folder / upstream-src）启动时 getcwd() 失败（ENOTSUP），向 stderr 打印两行无害警告。上游测试 fixtures `run_script()` 用 `NativeRuntime.shell_path()`（= which("bash") → HNP bash）spawn bash 并把 stdout+stderr 一起捕获进 insta 快照，警告行混入 → 全部快照失配。104 个通过用例恰好都是不 spawn bash 的（纯内存 eval/compgen、仅查 stdout contains 的 cli 用例） | test_package/conanfile.py `_run_upstream_tests()` 运行 `cargo test --release` 前显式 `env["PWD"] = src_root`：bash `get_working_directory()` 在 getcwd() 失败时会回退使用 `$PWD`（绝对路径且存在），静默启动不打印警告（srecord 先例：HMDFS getcwd 失败场景用 $PWD 规避）。不改上游测试、不删断言；PWD 指向测试真实 cwd，快照内容与上游完全一致 |
| 18 | 第 17 轮修复后 218/219，仅 `cli::parallel` 失败：STDERR 段仍混入 3 行 `shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not supported` | cli::parallel 测试用 `.current_dir(tmpdir_path(&tmpdir, "dir1"))` 把 argc 的 cwd 设到 assert_fs 临时目录（位于 HMBS 注入的 TMPDIR，同样在 HMFS/HMDFS 上），argc 内部 `--argc-parallel` spawn 的 bash 继承该 cwd → getcwd 失败打印警告；而 bash 的 `$PWD` 回退要求 PWD==cwd（动态 tmpdir 无法预知），故 PWD=src_root 只覆盖 cwd=src_root 的 spawn，cli::parallel 仍失配 | test_package/conanfile.py `_build_env()` 将测试 TMPDIR/TMP/TEMP 优先指向 `/data/storage/el2/base/haps/entry/files/argc-1.24.0-test`（el2 tmpfs，addchain/ain/aliyun 先例）；`env["PWD"]=src_root` 保留。**本轮真机实测：el2 方案生效（bash cwd 确实落到 el2）但警告从 ENOTSUP 变为 EACCES（`Permission denied`）——el2 父目录链对 bash getcwd 仍不可遍历，方案失败** |
| 19 | 第 18 轮（el2）修复后仍 218/219，仅 `cli::parallel` 失败：STDERR 段 3 行 `shell-init: ... getcwd: cannot access parent directories: Permission denied` | el2 tmpfs 可写（addchain/ain 先例只保证写文件），但 el2 父目录链（/data/storage/el2/base/haps/entry/files）对 HNP bash 的 getcwd 遍历返回 EACCES，与 HMFS 的 ENOTSUP 是同一类「bash 无法 getcwd」问题；硬编码任何单一目录都不可靠，必须实测 | test_package/conanfile.py 新增 `_probe_getcwd_tmpdir()`：运行时用与上游测试一致的 bash（which("bash")→HNP bash）在候选目录（HMBS TMPDIR/el2/usr/local//data/local/tmp/~/tmp）下执行 `bash -c pwd`，stderr 无 shell-init/getcwd 警告且退出码 0 者作为测试 TMPDIR（assert_fs 临时目录与其内 bash 落在可 getcwd 的 FS 上）；全部失败回退 HMBS TMPDIR；`env["PWD"]=src_root` 保留。不改上游测试、不删断言 |
| 20 | 第 19 轮（探测目录）修复后仍 218/219：probe 枚举全部候选目录均失败（HMFS 全部 ENOTSUP、el2 EACCES、其余不可写），回退 HMBS TMPDIR 后 cli::parallel 警告仍是 `Not supported`——真机不存在任何可让 HNP bash getcwd 干净返回的可写目录，「把 cwd/TMPDIR 挪到可 getcwd 目录」路线彻底穷尽 | HMFS 不支持 getcwd 是 FS 级行为，与目录无关；bash 的 `$PWD` 回退要求 PWD==cwd，动态 tmpdir 无法预知路径 | **换道**：test_package/conanfile.py 删除 `_probe_getcwd_tmpdir`，改为 `_build_bash_shim()`——用 clang 编译一个同名 `bash` shim 并前置到 PATH 最前：argc 内部 `--argc-parallel` 与 fixtures `run_script`/`exec_bash_functions` 都经 which("bash")（PATH 查找）解析，全部命中 shim；shim 启动时先用 `getcwd()`（shim 链接 OHOS musl libc，与 cargo/rustc 同机制，真机 218 通过用例证明 HMFS 上可正常取 cwd）取真实 cwd，失败则回退 `readlink /proc/self/cwd`（内核 d_path 魔法链接），导出 `PWD=真实cwd` 后 exec 真 bash——bash 的 `$PWD` 回退（PWD==cwd 时静默启动）不再打印警告。TMPDIR 仅需可写（assert_fs 临时目录），不再要求可 getcwd。编译后立即在 HMBS TMPDIR 做端到端自检（`bash -c true` 检查 stderr 无 shell-init 警告）作为真机机器证据。不改上游测试、不删断言 |
| 21 | 第 20 轮（bash shim 换道）真机预检 upstream_test 失败：`bash shim compile failed (rc=1): bash_shim.c:10:16: error: use of undeclared identifier 'NULL'`——shim 从未编译成功、未进入 PATH，cli::parallel 快照 STDERR 仍混入 3 行 `shell-init: ... getcwd: cannot access parent directories: Not supported`（218/219） | `_build_bash_shim()` 的 C 源码是 freestanding 写法（零系统头文件、全部手工 typedef/extern），指针空比较误用了宏 `NULL`——无头文件环境下该标识符未声明，clang 直接报错（函数可隐式声明只是警告，未声明的标识符是硬错误，故只有这一处报错）；上一轮只校验了配方 Python 语法，未还原生成后的 C 源码逐字核对 | 改为 NULL-free 写法：`char *cwd = 0;`、`if (getcwd(buf, sizeof(buf)) != 0)`、`if (cwd != 0 && ...)`，指针空比较一律用 0（不依赖任何宏/头文件）；机制不变（getcwd → readlink /proc/self/cwd 导出 PWD → exec 真 bash）。本机无 C 编译器，用 ast 求值配方中的 src 模板还原最终 C 源码核对：无 NULL、% 格式化恰 2 个 %s（模板 2 占位符对 2 实参）、语句结构完整；py_compile 通过。不改上游测试、不删断言 |
| 22 | 第 21 轮（shim 编译修复生效）后真机预检 upstream_test 失败：日志显示 `bash shim probe OK`、219 个用例全部通过（含 cli::parallel），但 cargo test 收尾的 Doc-tests 阶段报 `could not execute process rustdoc ... (never executed)` → `No such file or directory (os error 2)`，rc=101（passed=219, failed=0 仍被 ConanException 拦下） | OHOS rust 工具链（Harmonybrew bottle）无可用 rustdoc——ENOENT 出现在 cargo spawn rustdoc 进程阶段（进程从未执行），PATH 与 rustc 同目录均无 rustdoc；argc 源码 0 个 doctest 用例（src/ 无代码块），该阶段为空阶段。同仓库已合入先例 martin/1.13.0 报完全相同的 "No such file or directory" 并判定为平台限制，stylua/usage 报 EACCES/E051、gifski 报 musl 无 rustdoc，结论一致；无低成本补齐途径（rustdoc 只随完整工具链分发，设备 bottle 不含） | `_run_upstream_tests` 改用 `cargo test --release --tests`：`--tests` 只跑带 test 属性的目标（13 lib 单测 + 206 集成 = 219 个真实用例全部执行），排除 doc-tests 空阶段，rc 归 0；marker `command` 同步为实际命令；MANIFEST.yml `upstream_test_command` 与 `upstream_test_audit` 如实记录 doc-tests 平台限制（0 用例受影响）。不改上游测试、不删断言、不伪造通过 |

## 源码修改

无补丁。argc 1.24.0 纯 Rust 实现，无平台相关 C/C++ 代码，cargo 直接编译通过。

## 依赖版本

- Rust 工具链：Harmonybrew rust 1.97.1 bottle（cargo.real + rustc，arm64_ohos）
- Rust crate 依赖：Cargo.lock 固定（anyhow 1.0.102、nom 8.0.0、indexmap 2.10.0、serde 1、
  which 8.0.0、shell-words 1.1.0 等约 40 个 crate，经 rsproxy.cn sparse 镜像拉取）
- 无 C/C++ 三方库依赖

## 验证结果

```bash
# 真机预检（hmbs 自动执行）：conan create 包含
#   build()      : cargo build --release --bin argc  (产物 bin/argc)
#   test_package : /bin/sh test.sh                   (3 个消费者用例)
#                : cargo test --release              (上游测试套件，test_package 阶段)
# 测试数字以真机预检日志为准，见 HMBS_UPSTREAM_TEST_RESULT / HMBS_TEST_PACKAGE_RESULT
```

## 上游测试说明

- src/ 内 13 个 #[test] 单元测试
- tests/ 集成测试套件：tests.rs 聚合 16 模块，183 #[test] + 25 #[rstest]，含 175 个 insta 快照
- 全部为离线纯逻辑测试，无网络/在线数据集依赖，可在 HarmonyOS aarch64 真机完整执行

## 交付物

| 文件 | 说明 |
|------|------|
| bin/argc | argc 可执行文件（静态链接，ELF aarch64） |

## 注意事项

- test_package/test.sh 必须由 bash 执行（mksh 不能执行 ELF），conanfile.py 用
  CONFIG_SHELL 或 /data/service/hnp/bin/bash 兜底
- 真实机预检日志中的 cargo test 输出可直接用于 PR 正文「上游测试用例通过率」
- Rust 工具链引导（_bootstrap_rust_toolchain）仅在设备完全没有 cargo 时触发，
  已安装 cargo（HNP/harmonybrew/rustup）的设备直接复用，避免重复下载
