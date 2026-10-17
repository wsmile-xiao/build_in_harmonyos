# libobjc 16.1.1 适配笔记

## 编译环境
- 构建系统: autotools-custom (GCC 顶层 configure + make)
- 编译器: clang/clang++ (native aarch64-linux-ohos)
- 状态: pending（本机前置适配完成，真机 shadow CI 待执行）

## 版本映射（重要）

| 项目 | 值 | 说明 |
|------|-----|------|
| Conan 包版本 | 16.1.1 | 按任务要求 |
| 上游源码版本 | GCC 16.1.0 | GCC 官方 ftp 无 gcc-16.1.1.tar.xz（只有 16.1.0 / 16.2.0）|
| 源码 tarball | gcc-16.1.0.tar.xz | sha256 `50efb4d9...510f79`（本机下载并复核，sha512 与官方一致）|

> **待确认**：若任务清单里的 "16.1.1" 明确指向 releases/gcc-16 分支的某个 git
> commit（而非 16.1 系列的官方 tarball），需改为 git archive 或换用 16.2.0，
> 并同步更新目录名、conanfile version、test_package 引用与分支名。

## 上游与依赖

- libobjc 是 GNU Objective-C runtime，无独立上游 tarball，源码位于 GCC 源码树
  `libobjc/` 子目录，必须从完整 GCC 源码构建。
- GCC 16 前端为 C++ 实现，构建需 clang + clang++。
- GCC 16 官方 download_prerequisites 选定的 in-tree 依赖：GMP 6.3.0、MPFR 4.2.2、
  MPC 1.3.1（已校验 sha256，见 conandata.yml）。
- ISL 可选，已 `--without-isl` 关闭；NLS 关闭后无需 gettext。

## 构建步骤（真机 shadow CI 预期）

```bash
# 1. 下载 GCC 16.1.0 源码 + gmp/mpfr/mpc（conanfile.py source() 自动完成）
# 2. source() 内应用 OHOS 源码变换（files/prepare_ohos_sources.py）：
#    - config.sub/configfsf.sub 注入 aarch64-linux-ohos triplet
#    - configure 脚本 umask 077 -> 022（HMDFS）
#    - gcc/config.gcc 的 aarch64 musl/ohos 映射
#    - 复制 gcc/config/ohos.h
# 3. configure:
#    --enable-languages=c,objc --disable-bootstrap --disable-multilib
#    --disable-nls --without-isl --with-sysroot=<OHOS sysroot>
# 4. make all-gcc           # 生成 gcc/runtime-info.h（libobjc 构建依赖）
# 5. make all-target-libgcc # libobjc 链接依赖
# 6. make all-target-libobjc
# 7. make install-target-libobjc DESTDIR=<package>
```

## 关键风险点

| # | 风险 | 说明 | 处理 |
|---|------|------|------|
| 1 | ~~gcc/config.gcc 漂移~~ | 已本机核对 gcc-16.1.0 源码：4 个 OHOS 映射 anchor 与 GCC 9 完全一致 | prepare 脚本可 applied 4/4，风险解除 |
| 2 | libobjc 目标启用 | 仅 `--enable-languages` 含 objc 时才构建 libobjc | 已设 `--enable-languages=c,objc` |
| 3 | 构建耗时 | GCC 16 c+objc 前端 + libgcc + libobjc 完整构建较重 | 错峰、单包排队；make 限 -j2 pipe jobserver |
| 4 | ELF 签名 | 生成的主机工具与编译器须签名才能执行 | 沿用 gcc/9.5.0 的 wrapper + _sign_elf_tree |

## 关键发现（本机核对 gcc-16.1.0 源码）

- **libobjc 为 C 实现**（configure.ac 用 AC_PROG_CC），构建 libobjc 无需 C++ 标准库，
  只需 xgcc（C 编译器）+ libgcc。
- **libobjc 用 modern API（objc/runtime.h）**，GCC 16 已移除 legacy `objc/objc-api.h`。
  关键 API：`sel_registerName`/`sel_getName`/`objc_getClass`/`class_getName`/
  `objc_getClassList`/`class_createInstance(cls, extraBytes)`/`object_dispose`。
  test_package/test_objc.c 已按 modern API 编写（纯 C，无需 @interface）。
- **内置根类**：Object / Protocol / NXConstantString 由 runtime 注册，`objc_getClass("Object")`
  可用作消费者验证入口（Object.h 用 @interface 语法，纯 C 测试不 include 它）。
- 非 cross 时 `toolexeclibdir=$(libdir)=/lib`，libobjc.so 安装到 `<package>/lib/`。


## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| gmp | 6.3.0 | bundled (gcc.gnu.org/pub/gcc/infrastructure) |
| mpfr | 4.2.2 | bundled |
| mpc | 1.3.1 | bundled |

## 验证结果

- 本机：源码 tarball 下载并 sha256 复核通过（sha512 与 GCC 官方 buildroot 记录一致）。
- 真机/shadow CI：pending。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | GCC 源码树构建 libobjc 子库的配方 |
| conandata.yml | GCC 16.1.0 + gmp/mpfr/mpc 源码 URL 与 sha256 |
| files/prepare_ohos_sources.py | OHOS 源码变换脚本 |
| files/ohos.h | OHOS target 定义头 |
| test_package/ | 消费者测试（L1）+ MANIFEST.yml |
| reports/W0-report.md | W0 依赖检查报告 |

## 注意事项

1. 本库与 `libobjc2`（GNUstep runtime，archives/l/libobjc2）是不同项目：
   libobjc2 是 Objective-C 2.0 runtime，libobjc 是 GCC 的 legacy GNU runtime。
2. 两者产物 SONAME 均为 libobjc.so，cpp_info.libs 均为 "objc"，不应在同一消费
   链同时混用。
3. 鸿蒙 libunwind 的 `_Unwind_Resume()` 平台限制（见 libobjc2 notes）同样会影响
   本库的 C++ 异常互操作，属平台限制而非本库缺陷。

## 下一步真机 / shadow CI 命令

```powershell
# 1. 连通性检查（真机空闲窗口；私钥路径与设备 IP 由任务现场提供）
ssh -i <private-key-path> -p 2222 `
  -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes `
  currentUser@<device-ip> "echo ok"
```

```sh
# 2. 创建隔离 job（设备端；无 git 时用 --repo-source 指向已有仓库）
job="libobjc-16.1.1-$(date +%Y%m%d%H%M%S)"
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job "$job" \
  --package archives/l/libobjc/16.1.1 \
  --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"

# 3. 传输本库目录后执行 runner
#   （二进制 tar 勿走 PowerShell 文本管道，用 scp 或 base64）
sh "$HOME/ohos-users/codex/$job/run-conan-heavy.sh"

# 4. 关注产物（L0/L1/L2/L4/L5）+ 上游测试 + test_package 结果
find "$job" -maxdepth 4 -type f -print
```

真机验证重点：`all-target-libobjc` 是否产出 libobjc.so/libobjc.a；
`gcc/config.gcc` 的 OHOS 映射替换是否匹配 GCC 16（prepare 脚本会打印 applied N/4）。

## 真机 shadow CI 迭代记录

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | generate() 报 `OHOS compiler wrappers require: llvm-objcopy, llvm-readelf` | 隔离 job PATH 不含 binutils，objcopy/readelf 在 `/data/service/hnp/binutils.org/binutils_2.45/bin/` | conanfile.py 增加 `_resolve_binutil()`：先 PATH 找 llvm-\*/plain，再 glob 搜索 binutils.org/ohos-sdk.org |
| 2 | build 阶段 `[Errno 28] No space left on device`（Copying sources to build folder） | 旧 recipe revision 的 2G source 缓存 + 新 source 2G + build 复制 2G 超出 HMDFS 用户存储空间 | 清理旧 cache（`conan-home/p/<旧revision>`）；用 `nohup ... &` 后台触发避免 ssh 断开 |
| 3 | ssh 长连接断开（Connection reset / write EPIPE） | 设备 SSH 服务对长连接不稳 | 短 ssh 轮询 + `setsid nohup sh run-conan-heavy.sh &` 后台执行，脱离 ssh 会话 |
| 4 | build() 报 `OHOS SDK sysroot headers were not found: /data/service/sysroot` | HMDFS 上 `os.path.realpath` 不解析 symlink，clang 路径推导 sysroot 错误 | `_resolve_realpath()` 先 `readlink -f` 再 realpath；glob 搜索 ohos-sdk.org/*/ohos/native/sysroot |
| 5 | configure 报 `C compiler cannot create executables`（exit 77） | wrapper 脚本 shebang `#!/bin/sh` 在 HMDFS 上 `bad interpreter: Permission denied`（chmod 不生效） | CC/CXX 改为 `shlex.join([bash, wrapper])` 显式用 bash 执行 wrapper |
| 6 | configure-gmp 报 `cannot determine how to define a 32-bit word` | 隔离 job PATH 无 `llvm-nm`（gmp 的 asm 检测直接调 llvm-nm） | AR/RANLIB/NM 用 `_resolve_binutil()` 解析绝对路径；PATH prepend `/data/service/hnp/bin` |
| 7 | configure 报 `working directory cannot be determined`（getcwd 失败） | HMDFS 剥离父目录读权限，bash 启动 getcwd 失败 | build() 里 `os.environ["PWD"] = str(self.build_folder)`（bash 读 $PWD 不 getcwd）+ `--enable-serial-configure` |
| 8 | gmp mpn 报 `m4-ccas: /bin/sh: bad interpreter` | gmp 的 asm 辅助脚本 m4-ccas/cpp-ccas 由 libtool 直接执行 | prepare 脚本给 `gmp/mpn/Makefile.in`+`Makeasm.am` 的 m4-ccas/cpp-ccas 加 `$(SHELL)` 前缀 |
| 9 | all-build-libcpp 报 `move-if-change: /bin/sh: bad interpreter` | GCC 的 move-if-change 脚本直接执行 | prepare 脚本给 `libcpp/Makefile.in`+`gcc/Makefile.in`+`gcc/c/Make-lang.in` 的 move-if-change 加 `$(SHELL)` 前缀 |

已确认：`config.gcc applied 4/4`（OHOS 映射与 GCC 9 一致）；L0 全过；源码清华镜像下载成功；
clang 为 symlink 指向 `ohos-sdk.org/.../native/llvm/bin/clang`，sysroot 推导正确。


