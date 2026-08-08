# libx11 6.4.0 前置适配笔记

## 版本结论

- `libx11/6.4.0` 不是上游 libX11 源码版本；上游仍使用 `1.x` 版本号。
- 本仓库软件级 `manifest.yaml` 历史记录把 `6.4.0` 标为 published，旧下游 notes 也通过 cmd-pkgs 安装 `libx11 6.4.0`。
- cmd-pkgs 资产为 `libx11-6.4.0-ohos-aarch64.tar.gz`，内含 `libX11.so.6.4.0`、`libX11-xcb.so.1.0.0` 和 X11 headers。
- 本 Conan 配方保留 `libx11/6.4.0` 作为兼容 ref，源码使用官方 `libX11-1.8.10.tar.xz`，因为该源码的 libtool 版本生成 `libX11.so.6.4.0`。

## W0 依赖检查

已在本机查询 `ohpcd`：

| 依赖 | 状态 |
| --- | --- |
| xorgproto/2025.1 | 可查询到 |
| xtrans/1.6.0 | 可查询到 |
| xcb-proto/1.17.0 | 可查询到 |
| libxau/1.0.11 | 可查询到 |
| libxcb/1.16 | 可查询到；2026-08-08 复验通过 |
| libx11/* | 未查询到 |

`libX11-1.8.10/configure.ac` 中 `X11_REQUIRES='xproto >= 7.0.25 xextproto xtrans xcb >= 1.11.1'`，且 `src/Makefile.am` 将 `xcb_disp.c`、`xcb_io.c` 编入 `libX11` 本体；不是可干净关闭的可选模块。

## 配方策略

- 使用 Autotools 源码构建，而不是把 cmd-pkgs 二进制重新打包成无依赖 Conan 包。
- 显式声明 `libxcb/1.16` 依赖，避免隐藏 `libX11.so.6` 对 `libxcb.so.1` 的运行时需求。
- 关闭 specs/xmlto/fop/xsltproc 文档生成，保留上游 `make check`。
- `test_package` 编译并运行一个 Xlib 消费者，覆盖 `XInitThreads`、`Xresource`、keysym、error handler 和 `Xlib-xcb` 符号引用，不连接 X server。
- OHOS Autotools triplet 使用 `aarch64-unknown-linux-ohos`，与已合入的 `libxcb/1.16` recipe 保持一致；补丁让上游 `config.sub` 接受 `ohos`/`linux-ohos`，让 `configure` 临时目录遵循 `TMPDIR`，并在 `linux-ohos` clang 场景下把 `RAWCPP` 修正为显式 stdin 形式。
- 借鉴 `libxcb/1.16` 真机修正：recipe 不再硬编码 `/data/service/hnp/bin/bash`，而是解析可执行 shell；同时 bootstrap PATH，并在配置文件中的 clang 路径不存在时回退到 PATH 中的 clang。
- OHOS 下不生成 `AutotoolsDeps` 的全局 `LIBS`，避免 libxcb 所有扩展库被注入到 libX11 链接命令；libxcb/libXau/libXdmcp 的 `.so` 会被 staging 到 build folder 的无 `.la` 目录，规避依赖包 `.la` 中旧 build 路径导致的 libtool 解析失败。

## libxcb 合入后复验

`libxcb/1.16` 已在 `ohpcd` 可解析：

```powershell
conan download "libxcb/1.16" -r=ohpcd --only-recipe
```

本机已完成的前置验证：

```powershell
python -m py_compile archives/l/libx11/6.4.0/conanfile.py archives/l/libx11/6.4.0/test_package/conanfile.py
git -C D:\harmonyos\tmp\libx11-1.8.10-source\libX11-1.8.10 apply --check D:\harmonyos\worktrees\libx11\archives\l\libx11\6.4.0\patches\0001-support-ohos-configure.patch
conan inspect archives/l/libx11/6.4.0
conan graph info archives/l/libx11/6.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
conan install archives/l/libx11/6.4.0 -of D:\harmonyos\tmp\libx11-conan-install -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
conan export archives/l/libx11/6.4.0
git diff --check -- archives/l/libx11/6.4.0
```

`conan install` 生成的 `conanbuild.conf` 已确认包含：

```text
--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos
```

当前工作机是 Windows 环境，`where.exe zsh` 未找到项目要求的 `zsh`；`bash.exe -lc "command -v zsh"` 进入 WSL 后没有可用 zsh/conan，并输出 podman run-root 权限告警。因此本机只做前置验证，OHOS 单包 CI 改在用户提供的远端机器执行。

## 远端单包 CI 结果

2026-08-08 在 `currentUser@frp-tip.com:33332` 启动单包构建，远端仓库为 `/storage/Users/currentUser/validation/build_in_harmonyos`：

```sh
CI_PACKAGES="archives/l/libx11/6.4.0" /usr/bin/zsh ci/conan/build_and_test.sh
```

最终通过，日志：

```text
/storage/Users/currentUser/libx11-ci-review2-20260808-153637.log
```

关键结果：

- `libx11/6.4.0#63e25e48c3af73db324ce61d0dba9cce:c042bc3ef1476cfe65d9b8d95c3088cf1ad1a5ab#f40ea57b2dfab93b3acd36f7458f6887` 创建成功。
- `perl/5.42.2` 作为 build requirement 从 Conan 构建环境进入 PATH，`configure` 记录 `checking for perl... /storage/Users/currentUser/.conan2/p/perlbad96edf51f7f/p/bin/perl`。
- `make -j20`、上游 `make check -j20`、`make install` 均通过；`make check` 执行 `compose-check.pl`，汇总 `TOTAL: 1`、`PASS: 1`、`FAIL: 0`、`ERROR: 0`。上游测试通过率按已注册可计数测试写为 `1/1（100%）`，不把消费者测试计入上游测试。
- `test_package` 编译并运行 `libx11_consumer`，输出 `libx11 consumer smoke passed: quark=3 keysym=65`。
- CI gate：`L0_RESULT=pass`、`L1_RESULT=pass`、`L2_RESULT=skip: no bin/ dir`、`L4_RESULT=pass`、`L5_RESULT=pass`。
- Build Summary：`Total: 1`、`Success: 1`、`Failed: 0`，runner 退出码 0。

本轮远端调试中确认并修复的两个 OHOS 专有问题：

- X.Org `XORG_PROG_RAWCPP` 假设 `${CC} -E < conftest.c` 会读取 stdin；OHOS clang driver 需要显式 `-x c -`，否则 RAWCPP 探测会误报 `defines unix` 或 `does not preserve whitespace`。
- 已合入的 `libxcb/1.16` 产物中 `.la` 的 `dependency_libs` 带有旧 build-folder 路径，libtool 链接 libX11 时会追踪这些 `.la` 并失败；libx11 recipe 通过无 `.la` 的 `.so` staging 目录规避，不修改 libxcb 包缓存或配方。
- AI review 建议恢复 Autoconf 临时目录的 `umask 077`；真机探针和 CI 复跑确认 `(umask 077 && mktemp -d ...)` 在 HMDFS 上生成 `drwx--S---`，后续 `config.status` 写 `subs1.awk` 会 `Permission denied`。本配方保留项目共性指南中的 OHOS/HMDFS 兼容处理：临时目录改到 `${TMPDIR:-.}`，并使用 `umask 022`。

## 后续验证命令

```sh
conan download "libxcb/1.16" -r=ohpcd --only-recipe
CI_PACKAGES="archives/l/libx11/6.4.0" zsh ci/conan/build_and_test.sh
```

如走真机影子 CI：

```sh
/path/to/run-ohos-shadow-ci.sh archives/l/libx11/6.4.0
```

## 本机记录

- `git fetch origin`：2026-08-08 成功刷新到包含 `libxcb/1.16` 的 `origin/main`。
- `git rebase origin/main`：成功，worktree 仍只新增/修改 `archives/l/libx11/6.4.0/`。
- 分支：`feat/libx11-6.4.0`
- issue：未在项目文件中找到明确编号，待补。

## 最终状态

built。远端 OHOS 单包 CI、上游 `make check`（1/1，100%）、消费者 `test_package` 均已完成并通过；issue 编号按本轮要求忽略。
