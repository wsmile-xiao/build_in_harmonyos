# udns 0.6 适配笔记

## 编译环境
- 构建系统: 自研 autoconf 风格（configure + configure.lib + Makefile.in）
- 编译日期: 2026-09-18
- 编译器: clang（OHOS /data/service/hnp/bin/clang，native 编译）
- 三元组: aarch64-linux-ohos（native 编译，非交叉）
- 状态: built（本地 gcc 验证通过，真机预检由 hmbs 执行）

## 编译步骤

```bash
# 1. 解压官方源
tar xzf udns-0.6.tar.gz && cd udns-0.6

# 2. configure（就地构建；udns configure 不接受 --prefix，仅支持 IPv6 选项）
sh ./configure --enable-ipv6

# 3. 构建静态库（不使用示例工具，保持库级最小产物）
make staticlib -j1
# 产物: libudns.a（+ 构建期生成 udns_codes.c 与 config.h）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | udns 自带 configure 不接受 `--prefix`/`--host` 等 GNU autoconf 选项 | 上游为自研 configure 脚本（configure.lib），仅支持 `--enable/--disable-ipv6` 与 `--help` | 不使用 `Autotools(self).configure()`，改为手动就地运行 `configure` + `make staticlib` |
| 2 | `Makefile` 无 `install` 目标，`conan create` 无法自动安装 | 上游 Makefile.in 仅含 all/static/***lib/dist/clean 等目标 | `package()` 手动 `copy` `libudns.a` 与 `udns.h` 到 package 目录 |
| 3 | `Makefile` 非 VPATH（SRCS 为裸文件名），out-of-source 构建找不到源文件 | 上游 Makefile 直接在 cwd 引用 `udns_dn.c` 等 | `build()` 中 `cd` 到源码目录就地构建（configure + make 均在 source_folder） |
| 4 | `self.run()` 中不能裸用 `${CC}`（R33） | configure 用 `$CC`/`$CFLAGS` 环境变量探测编译器 | 由 `AutotoolsToolchain` 生成的 conanbuild env 提供编译器，`self.run(..., env="conanbuild")` |
| 5 | 上游无测试套件（无 check/test 目标、无 tests/ 目录） | udns 为纯库，官方不提供自动化测试 | `test_package/MANIFEST.yml` 声明 `upstream_tests_exist: false` 并附完整审计；`test_package` 以 11 项断言实质调用 libudns API 验证 |
| 6 | 真机预检 `conan create` 报 `ERROR: udns/0.6: Package type is 'library', but no 'shared' option declared` | Conan 2 要求 `package_type="library"` 必须声明 `shared` option，旧配方未声明 | 配方声明 `options = {"shared": [True, False]}` 与 `default_options = {"shared": False}`；static-only（`make staticlib`），无论 option 取值均只构建静态库 |
| 7 | 真机预检 `build()` 报 `/bin/sh: make: No such file or directory`（missing_build_tool）+ configure 阶段 `/tmp/shk7julx.tmp: Read-only file system`（readonly_tmp） | ① 真机 make 位于 /data/service/hnp/bin/make 且不保证在子进程 PATH 上，配方裸写 `make staticlib` 找不到；② OHOS `/tmp` 只读，configure/conftest 与 mktemp 默认写 `/tmp` 失败 | ① `build()` 改由 `HMBS_MAKE`（真机注入绝对路径）→ `shutil.which("make")` → `"make"` 三级解析 make 二进制，不再假定 PATH；② 将 `TMPDIR/TMP/TEMP` 指到 HMBS 注入的可写 tmpdir（回退 build_folder/.tmp）并 `os.makedirs`；③ 不再硬编码 HNP bash，改用 HMBS 注入的 `CONFIG_SHELL/SHELL`（真机 `/bin/sh`）驱动 configure，规避 shell_getcwd |

## 源码修改（补丁）

- **无补丁**：udns 0.6 源码在 clang/HarmonyOS 上可直接编译，无需 config.guess/config.sub 或平台宏适配（POSIX socket/网络接口齐全，IPv6 由 configure 探测启用）。
- test_package/test.c 增补 `HMBS_TEST_PACKAGE_RESULT` 硬门禁标记（discovered=11、passedCount 与 RESULT 行同一计数器），满足 hmbs 机器证据要求。

## 依赖版本

- **无外部依赖**：纯 C 库，仅依赖系统 libc 与 POSIX socket/arpa/inet 接口。

## 验证结果

本地 gcc 编译 + test_package 验证（11 项断言全过，退出码 0）：

```
test_udns: linking against udns 0.6
dns_init(NULL,0) returned 0
dns_version() = 0.6
dns_sptodn length = 17
dns_dntosp = www.example.com
dns_dntop = www.example.com
dns_pton = 1
dns_ntop = 192.168.1.1
dns_strerror(DNS_E_NXDOMAIN) = domain name does not exist
test_udns: RESULT 11/11 checks passed (udns 0.6)
```

反向证伪：将某一断言期望值改为错误值后，测试报 `RESULT 10/11 checks passed, 1 FAILED` 且退出码 1，证明测试确实能捕获失败（honest harness，非空壳）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（自研 autotools，就地构建静态库，手动打包） |
| conandata.yml | 官方源 URL + sha256 |
| test_package/ | 消费者测试（11 项断言调用真实 libudns API） |
| manifest.yaml | 版本级 + 软件级 manifest |
| notes.md | 本笔记 |

## 注意事项

1. 本适配只打包 `libudns.a`（静态库）与 `udns.h`，示例工具 `dnsget`/`rblcheck`/`ex-rdns` 不打包 → 无 bin/，无需 commands.json（R38）
2. 版本号 0.6（首次适配，不加后缀，R37）
3. settings.os 判断用 `in ("Linux", "OHOS")`（R32）
4. build() 不依赖未定义 shell 环境变量（R33），编译器来自 AutotoolsToolchain conanbuild env
5. configure 用 `CONFIG_SHELL`（默认 /data/service/hnp/bin/bash）驱动，规避 OHOS /bin/sh 缺失（R5）

---

**编译结束**: 2026-09-18
**最终状态**: built（待真机预检）

## 真机 evidence 修复（2026-09-18 第二轮）
- 真机预检标记为 incomplete：缺失 `HMBS_UPSTREAM_TEST_RESULT` 上游测试证据（上游测试发现/执行/通过均为 0）。
- 根因：udns 0.6 上游确实无测试套件（MANIFEST.yml `upstream_tests_exist: false` + 完整审计），但本配方未在任何实际运行的环节复发上游测试 `no_tests` 标记（此前只有 test.c 输出 `HMBS_TEST_PACKAGE_RESULT`）。
- 修复：test_package/conanfile.py 的 test() 在真实运行 test_udns（11 项断言，含 HMBS_TEST_PACKAGE_RESULT）之后复发 `HMBS_UPSTREAM_TEST_RESULT`，status=no_tests、discovered/executed/passed/failed/skipped 均为 0，并带 reason 引用 MANIFEST 的 upstream_test_audit。这与仓库其他 no_tests 库（如 asterisk-flite）被放行的接入方式一致。
- 每轮必跑的 test() 复发标记，规避 `conan create` 缓存命中（Already installed!）时主配方 build() 不执行导致 evidence 缺失的问题。
