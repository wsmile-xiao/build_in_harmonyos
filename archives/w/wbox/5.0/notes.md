# wbox 5.0 适配笔记（上游版本标识为 "5"）

> 版本号说明：上游只给出单数字版本 "5"（tarball `wbox-5.tar.gz`、`wbox -v` 输出
> `WBox version 5`）。Conan 2.29.1 的 `RecipeReference.validate_ref()`
> （`conan/api/model/refs.py:148`，正则 `^[a-z0-9_][a-z0-9_+.-]{1,100}\Z`）
> 要求版本号至少 2 字符，单字符版本在 `conan create` 导出阶段被拒
> （实测首错：`ERROR: Invalid package version '5'`），因此规范化归档版本为 `5.0`。
> 仓库既有同类先例：btyacc（上游 "3" → 配方 "3.0"，
> 见 `knowledge/drafts/DRAFT-btyacc-3.0-conan-single-char-version.md`）。

## 编译环境

- 构建系统: makefile（上游为纯 Makefile，无 configure）
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4（OHOS 工具链，`aarch64-linux-ohos` / musl）
- 目标平台: HarmonyOS PC（aarch64）
- 状态: built（配方经 conan create 实测通过，未上传制品仓）
- 源码: wbox-5.tar.gz，sha256 `1589d85e83c8ee78383a491d89e768ab9aab9f433c5f5e035cfb5eed17efaa19`

## 编译步骤

上游源码只有 13 个文件，Makefile 的默认目标即 `wbox`：

```bash
# 1. 解包（conan source() 用 get() 完成，strip_root=True）
tar xzf wbox-5.tar.gz

# 2. 直接编译（无 configure；CC 取自 Conan toolchain，R33）
make CC=clang CFLAGS="-O2 -Wall -W" DEBUG="" -j1
#   clang -c -O2 -Wall -W   anet.c
#   clang -c -O2 -Wall -W   sds.c
#   clang -c -O2 -Wall -W   wbsignal.c
#   clang -c -O2 -Wall -W   wbox.c
#   clang -o wbox -O2 -Wall -W  anet.o sds.o wbsignal.o wbox.o

# 3. 安装（conan package() 用 copy() 完成）
#   bin/wbox + licenses/COPYING + share/wbox/{README,Changelog}
```

退出码 0，产物 `bin/wbox`（47488 字节，ELF 64-bit LSB ARM aarch64，
动态链接 `/lib/ld-musl-aarch64.so.1`，PIE + non-exec stack）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游官方下载 URL 404 | hping.org 站点改版为 WordPress 页面后不再提供 wbox-5.tar.gz | 使用 Fedora lookaside 缓存的上游原样 tarball（sha256 与 Debian orig 一致，解包树 diff 为零） |
| 2 | `ERROR: Invalid package version '5'`（conan create 导出阶段） | Conan 2.29.1 要求版本号 ≥2 字符，上游单数字版本 "5" 不合法 | 归档版本规范化为 `5.0`（版本目录 / conanfile.py / manifest / commands.json / 分支名五处同步），上游源码与产物不变 |
| 3 | `make -j2` 报 `jobserver mkfifo: Operation not permitted` | 鸿蒙 `$TMPDIR` 不允许 make jobserver 创建 fifo | 统一用 `-j1`（R9） |
| 4 | 二进制内嵌宿主构建路径 | 上游 Makefile `DEBUG?= -g` 默认带调试信息，DWARF 里含 `/storage/.../wbox-5.work` | Release 构建显式 `DEBUG=` 清空；鸿蒙专项测试 T3 复核无路径泄漏 |
| 5 | `wbox.c:1186` 编译告警 `variable 'flags' set but not used` | 上游代码自身问题（与平台无关） | 不修：不影响功能，避免为非平台问题引入补丁 |

## 源码修改

无补丁（零 `patches/`）。上游代码在 OHOS/arm64 上原样编译通过。

## 依赖版本

无第三方依赖（仅工具链 libc + POSIX）。`init-build` 依赖解析与
`ci/scripts/preflight_check.sh wbox/5` 均报"无依赖需要检查"。

## 验证结果

```bash
# 1. 基础 CLI 契约（test_package/test.sh）            日志: reports/logs/test-sh.log
$ wbox -v
WBox version 5
$ wbox            # 无参数 -> usage 横幅
Usage: wbox <url> [options ...]

# 2. 上游教程等价的人工入口（hping.org/wbox/ 的 client/server 模式）
$ wbox servermode webroot <dir> serverport 18081 &
$ wbox 127.0.0.1:18081/index.html 1 showhdr dump
HTTP/1.1 200 OK  ... 0. 200 OK    725 bytes    4 ms
--- 1 replies received, time min/avg/max = 4/4.00/4 ---

# 3. 鸿蒙特有测试（test_package/test_wbox_ohos.sh）    日志: reports/logs/test-wbox-ohos.log
== wbox HarmonyOS-specific test ==  (12 项断言全 PASS)
  [PASS] T1 ELF machine = AArch64 / T1 PIE (ET_DYN)
  [PASS] T2 musl loader: /lib/ld-musl-aarch64.so.1 / T2 no glibc linkage
  [PASS] T4 non-executable stack (GNU_STACK RW) / T3 no host build path in binary
  [PASS] T5a HTTP 200 + payload intact / T5b 404 Not Found
  [PASS] T5c clients 2 (fork) -> 6 x 200 OK replies
  [PASS] T5d connection refused -> exit 3 / T5e server log records serving
== OHOS test PASSED ==

# 4. 配方复现（conan create，含 test_package 自动执行） 日志: reports/w3-local-ci.log
```

## 上游测试清点（R51）

上游 wbox 5 **没有自动化测试套件**，清点证据：

- 源码包顶层仅 `AUTHORS COPYING Changelog Makefile README TODO *.c *.h`，
  无 `tests/`/`test/` 目录、无 `test_*.c`
- `Makefile` 目标只有 `all` / `wbox` / `clean` / `dep`，**没有 `check`/`test`**
- 源码内 `grep -c 'assert(' *.c` = 0，无断言式自测
- 无 CI 配置（无 `.travis.yml`/`.github/`）、无 `configure.ac`/`CMakeLists.txt`

上游可统计用例数 = **0**（通过 / 失败 / 跳过 均为 0）。
上游文档（<https://www.hping.org/wbox/>）给出的唯一验证方式是人工按教程操作
client/server 模式——本归档把该入口自动化成 `test_wbox_ohos.sh` T5 端到端验证。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/wbox` | 47488 B | HTTP 测试 CLI（client + servermode） |
| `licenses/COPYING` | 1631 B | New BSD 许可证 |
| `share/wbox/README`、`Changelog` | 50 B / 659 B | 上游文档 |

## 注意事项

- 上游项目自 2009 年起未再更新（v5 为最终版），源码 URL 已在 hping.org 失效，
  后续如需复现请使用 conandata.yml 中的镜像 URL（CI 亦有镜像回退）。
- `wbox` 的 `clients <n>` 会 fork，在受限 cgroup/无 fork 权限环境中会失败；
  OHOS PC 上实测正常。
---

**编译结束**: 2026-09-23 13:57
**最终状态**: built
