# libcdio 2.3.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build libcdio 2.3.0` — 初始化构建环境
2. 下载源码并解压到 `~/tmp/builds/libcdio-2.3.0.work`
3. 运行 `patch-autotools-ohos.pl config.guess config.sub` — 为 OHOS 打补丁
4. 修改 `configure` 脚本中的 umask 077 → umask 022（HMDFS 兼容性）
5. `./configure --prefix=/storage/Users/currentUser/usr/local`
6. 生成 config.status 后，同样修改其 umask 077 → umask 022 + chmod 755
7. 运行 `./config.status` 生成所有 Makefiles
8. `make -j2`
9. `make install DESTDIR=$TEST_PREFIX` — staging 安装
10. staging 验证通过
11. `make check` — 20 PASS, 2 SKIP, 1 XFAIL, 1 FAIL (平台限制)
12. `verify-build` — G1-G4 PASS
13. `ohc-run.py package` — 打包预编译包
14. `make install` — 本地安装（无 DESTDIR）
15. 用户验证通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不含 OHOS 检测 | `patch-autotools-ohos.pl config.guess config.sub` |
| 2 | config.status 创建临时目录后无法写入文件 | HMDFS 上 mktemp -d 配合 umask 077 创建的目录权限为 drwx--S---，HMDFS 拒绝写入 | 修改 configure 和 config.status 中 umask 077 → umask 022，并添加 chmod 755 |
| 3 | check_udf.sh 测试失败 | E002: 测试硬编码 /tmp 为提取目录，OHOS 上 /tmp 为只读 | 平台限制，非软件缺陷 |
| 4 | libcddb 未找到 | 未安装 libcddb 预编译包 | CDDB 功能被禁用，非必需 |
| 5 | ncurses 未找到 | ncurses 未以 pkg-config 可发现方式安装 | cdda-player 被禁用，非必需 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| config.guess | OHOS LIBC 检测 + HarmonyOS 系统识别（patch-autotools-ohos.pl） |
| config.sub | ohos-linux 三元组 + linux-ohos 内核（patch-autotools-ohos.pl） |
| configure | umask 077 → umask 022 + chmod 755 $ac_tmp（HMDFS 兼容） |

## 依赖版本

- clang 15.0.4
- GNU Make 4.4.1
- autoconf 2.72 / automake 1.17

## 验证结果

```
$ cd-drive --version → cd-drive version 2.3.0 aarch64-unknown-linux-ohos
$ cd-info --version → cd-info version 2.3.0 aarch64-unknown-linux-ohos
$ iso-info --version → iso-info version 2.3.0 aarch64-unknown-linux-ohos
$ pkg-config --modversion libcdio → 2.3.0
$ pkg-config --modversion libiso9660 → 2.3.0
$ pkg-config --modversion libudf → 2.3.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcdio-2.3.0-ohos-aarch64.tar.gz | 2.3M | 预编译包（含 bin/lib/include/pkgconfig） |
| libcdio-2.3.0-ohos-aarch64-debug.tar.gz | 954K | 调试符号包 |

## 注意事项

- HMDFS 上 umask 077 + mktemp 创建的目录无法写入文件，需改为 umask 022
- 1 个测试失败（check_udf.sh）是平台限制（/tmp 只读），不影响功能
- CDDB 和 cdda-player 功能因缺少 libcddb/ncurses 而被禁用，对核心库功能无影响
---

**编译结束**: 2026-05-28 10:59
**最终状态**: built

## Conan 配方固化（2026-08-24）

本次在历史 OHOS 归档基础上补齐了 `conanfile.py`、`conandata.yml` 和真实
`test_package/`。配方声明静态 `cdio`、`iso9660`、`udf` 三个库；
`pkg-config` 和 `cmake` 作为构建环境工具使用，不写入包的运行时依赖。

验证结果：

- 早期 `-pr:h=default -pr:b=default` 运行仅是本机 native smoke test，不能作为
  OHOS 交叉验证依据；本节的 OHOS 结果见下方“Conan/WSL 交叉验证”。
- 本机缺少系统 `pkg-config`/`cmake` 时，曾使用 Conan Center 缓存工具完成一次临时 native 验证；这些工具未写入最终配方依赖，避免 CI 私有 remote 缺包。
- macOS 仍不能直接验证 OHOS profile：当前社区源提供的 `conan-2.29.1` 在 macOS 上不包含 `settings.os=OHOS`，执行 `conan create ... -pr:h=ci/conan/profiles/ohos-aarch64` 报 `Invalid setting 'OHOS'`，因此 macOS 结果不计作 OHOS 成功。
- WSL2 `x86_64` 已完成真实 OHOS 交叉验证：使用 OHOS host profile + 原生 Linux build profile 执行 `conan create`，库构建、打包和 `test_package` 均通过，CTest 结果为 `1/1 Passed`。
- 为支持无鸿蒙设备的 WSL 验证，OHOS `test_package` 使用静态链接，并通过 `qemu-aarch64-static` 执行；正式 OHOS 运行时仍应在原生 OHOS 环境复核。
- OHOS 的 `iconv` 符号由 `libc.so` 提供，配方在 OHOS 下不再额外链接不存在的 `libiconv`。

## Conan/WSL 交叉验证（2026-08-24）

WSL2 `x86_64` 使用 OHOS host profile 和原生 Linux build profile 完成了真实的
OHOS 交叉构建。使用绝对 profile 路径，避免当前 WSL Conan 将相对的
`-pr:h` 参数错误解析为默认 profile：

```bash
conan create archives/l/libcdio/2.3.0 \
  -pr=/root/HarmonyPC/ci/conan/profiles/ohos-aarch64 \
  -pr:b=/root/.conan2/profiles/default \
  -o "libcdio/*:shared=False" \
  --build=missing
```

验证结果：

- `conan create` 返回码为 0，OHOS armv8/clang 15 目标库完成构建和打包。
- `make check` 汇总为 48 个上游用例：31 PASS、16 SKIP、1 XFAIL、0 FAIL；
  可执行的非 SKIP/XFAIL 用例通过率为 `31/31 (100%)`。
- `test_package` 的 CTest 为 `1/1 Passed`，消费者程序实际调用了
  `iso9660_open`、`udf_open` 和版本 API。
- WSL 没有 OHOS 设备和 `/lib/ld-musl-aarch64.so.1`，因此 OHOS 可执行文件通过
  libtool 的 `-all-static` 选项静态链接，并由 `qemu-aarch64-static`/binfmt
  执行交叉测试；这只用于本地交叉验证，不替代真实设备运行时验证。
- OHOS 配方统一加入 `-all-static`，使 Worker 上的 configure 探测、上游测试和
  Linux/QEMU 交叉测试使用一致的自包含可执行文件；此前去掉该参数会在 Worker
  的 `configure` C 编译器链接探测阶段失败。

此前归档中的 `make check` 失败记录属于 2026-05-28 的设备/HMDFS 环境，保留作
历史记录；本次 Conan 配方在 WSL 的完整上游测试结果以本节为准。

## CI 失败修复（2026-08-24）

AtomGit CI Worker 的 OHOS 构建在 `make check` 阶段暴露了上游
`test/check_udf.sh` 的平台假设：脚本将 UDF 解包目录硬编码为 `/tmp/udf-$$`，而
该 Worker 的 `/tmp` 为只读文件系统，导致 `check_udf.sh` 返回失败。编译本身及
其余测试均已完成。

新增 `0004-check-udf-use-tmpdir.patch`，同时修复 `test/check_udf.sh` 及其
`test/check_udf.sh.in` 模板，让该测试按 `TMPDIR`、`TMP`、`TEMP`、`/tmp` 的顺序
选择临时目录；不改变测试内容，只修正 OpenHarmony 临时目录路径。

修复后的 WSL Conan 复验结果：

- 上游 `test/driver`：16 个用例，9 PASS、7 SKIP、0 FAIL。
- 上游 `test`：24 个用例，19 PASS、4 SKIP、1 XFAIL、0 FAIL。
- `test_package`：CTest `1/1 Passed`。
