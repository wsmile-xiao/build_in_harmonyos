# jigit 1.22 适配笔记

## 编译环境
- 构建系统: makefile（顶层手写 Makefile：只有 all/lib 两个目标，无 configure、无 install）+ libjte/ 内嵌 autotools/libtool 子项目（AC_INIT 2.0.0，LT 2:0:0，SONAME libjte.so.2）
- 编译日期: 2026-09-27
- 编译器: clang / clang++（profile ci/conan/profiles/ohos-aarch64，Conan 2.29.1）
- 源码: https://www.einval.com/~steve/software/JTE/download/jigit-1.22.tar.xz —— 307884 B / sha256 8a1da3fb7b817174c6c19d71ede19a4b8d0ae433fc5e967d33abf74b545f9954 / 91 项（与 Debian 池件逐字节同一，池哈希可当官方哈希）
- 状态: built

- 编译状态：通过 —— conan create 全绿（create15 CREATE_RC=0；**交付态** RREV 50c30c85e4ebe8e551f31effc1b1e757、PKGID 529476831f2a99ec232a22521c08390fad2c47ea；W3 绿跑当时的 RREV 是 6b36e295820ad10ee1d591e0e4494eb1（file:// 预取件），两档差异见本文件末段「RREV 两档如实披露」条）
- 测试状态：通过 —— test_package/test_jigit.sh 打印 SUMMARY jigit consumer: total=29 passed=29 failed=0
- 运行状态：部分可用 —— libjte.so.2 + 7 个 C 工具 + jigdo-gen-checksum-list（#!/bin/sh）+ jte-demo 实测可跑；Perl 件（mkjigsnap、iso-image.pl）本机无 /usr/bin/perl，配方把 shebang 改写为 #!/usr/bin/env perl 后走 HNP perl（/data/service/hnp/bin/perl）可启动；上游 jigit 包装脚本（#!/bin/bash，且写死 apt/wget 流程）本机无 /bin/bash，配方不打包该件

## 编译步骤
1. libjte/：逐个 chmod +x configure config.guess config.sub install-sh missing compile ltmain.sh depcomp（HMDFS 落盘 0660）；在 libjte/configure 里重锚 config.status 的 scratch 目录；再 sh ./configure（args 见 manifest.yaml，剔除 AutotoolsToolchain 注入的 --disable-static）+ make -j1（必须 in-source，父 Makefile 直接吃 libjte_libjte_la-*.o）
2. 顶层：make -j1（其 all 目标内部再递归进 libjte，故先建 libjte 只是省一次全量）
3. package()：libjte 走 make install，7 个 C 工具与 man 页手工 copy，jigdo-gen-checksum-list 取自 libjte/bin，mkjigsnap 改 shebang，上游 noinst 的 test/demo 装成 bin/jte-demo；删除 libtool .la 残留

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 第一阶段 cannot guess build type 直接断 | E007：libjte 自带 config.guess 2018-02-24 / config.sub 2018-02-22 变体无 HarmonyOS 分支；scripts/patch-autotools-ohos.pl 实测只打中 1/5（其 __ANDROID__->LIBC、android-linux、linux-uclibc 三处锚点不存在，注入的 GUESS= 分支不回显不退出） | patches/0001 手工重锚：config.guess 加 aarch64:HarmonyOS -> aarch64-unknown-linux-ohos，config.sub 两处接受位放行 HarmonyOS/ohos；禁用 --build/--host 绕过（会被误判交叉编译、AC_RUN_IFELSE 全跳） |
| 2 | shell-init: getcwd / working directory cannot be determined | E386：Autoconf 2.69 序言用 $CONFIG_SHELL 重执行 configure，profile 的 [buildenv] 把 SHELL 指到 /data/service/hnp/bin/bash，重执行后 cwd 丢失 | build() 里 configure 调用前缀 CONFIG_SHELL=/bin/sh SHELL=/bin/sh，生成的 libtool/Makefile 继承该 SHELL |
| 3 | 顶层 make 链接 parallel-sums 报找不到/空目标文件 | AutotoolsToolchain 在 shared=True 时注入 --disable-static，libtool 把 libjte_libjte_la-*.o 换成 dummy 对象，而顶层 Makefile:10/13/16 正是吃这些 .o | 配方在 _configure_args() 里剔除 --disable-static，保留 libtool 默认 .a + .so（与 Debian libjte-dev 一致） |
| 4 | configure: error / ./confXXXXXX/subs1.awk: Permission denied | E129：HMDFS 上 toybox mktemp -d 返回 drwx--S---，内核拒绝在其内 O_WRONLY，config.status 的 here-doc 落不进 scratch | 配方 _relax_hmdfs_scratch_dir() 重锚 configure 内的 scratch 逻辑（改 configure 才有效：它是一次性生成 config.status 的母本） |
| 5 | libjte 编译/链接期 pthread_cancel 未定义 | OHOS musl 不实现 POSIX 线程取消 API | patches/0002 改走该文件自有的 quit 协议做线程拆除（置 quit 标志 + join），不再调 pthread_cancel |
| 6 | jigdo-gen-checksum-list 在 OHOS 上产出不被 libjte 接受的摘要清单 | 该脚本 case $SYSTEM 只列 Linux、GNU/kFreeBSD 两种，无 HarmonyOS 分支，uname -s 落到错误摘要类型 | patches/0003 把 HarmonyOS 并入 Linux 分支；测试第 23 条断言其产出 32 位十六进制 md5 清单 |
| 7 | 消费者测试第 27 条（create14 唯一失败项）前提写错 | 见下节「测试前提订正」 | 断言改为腐蚀 template 并核 rc + 上游错误链，分母不变 |

## 测试前提订正（第 27 条破坏性断言，create14 唯一失败项）

原断言：往镜像源文件 f1.bin 追加一个字节后，要求 jigit-mkimage 必须失败或产出不同镜像。实测 rc=0 且镜像逐字节相同，NOT OK。

判读=断言前提写错，不是打包缺东西：
- libjte/jte.h:105 `#define MIN_JIGDO_FILE_SIZE 1024`，本用例两个载荷分别是 34 B / 68 B（远小于阈值），jte-demo 因此把镜像整体压进 template 的数据块、.jigdo 的 [Parts] 段是空的（一手取数：round.jigdo 正文 [Parts] 与 [Servers] 之间无条目；同载荷换成 108894 B 的 f1.bin 时该行变成 4HH3B997vu4qah60gBHd0A=f1.bin）。
- mkimage.c:259-297 find_file_in_mirror() 只用 mirror_path + jigdo_name 拼路径后调 file_exists()，摘要取自 .jigdo 原文、从不重算；mkimage.c:1069/1242-1249 只对 template 尾部携带的镜像 MD5 做核。
- 因此在"载荷全内联"的形状下，改内容（追加/截断）甚至把 f1.bin 改名挪走，mkimage 都照旧 rc=0 输出同一镜像（三档实测见 ~/tmp/uc2/z74-jigit/probe27.sh 与 probe27d.sh，逐条 BASE_ID/A_ID/B_ID/C_ID 全为 yes）。
- 换成对 template 动手才是它真正消费的输入：中间一字节翻转 rc=5 + "ungzip_data_block: failed to decompress"，尾部一字节翻转 rc=22 + "Failed to find desc start in the template file"，两条都以 "Unable to recreate image from template file" 收尾且输出镜像不再等于原镜像（~/tmp/uc2/z74-jigit/probe27c.sh 实测）。
- 处置=三选一里的第①种：断言改为"腐蚀 template ⇒ 必须非 0 退出 + 命中上游可识别错误链 + 输出不逐字节等于 image.out"，仍是一条 ok/bad 站点，分母不变。同时补记：该形状下 mkimage 不复核镜像源文件内容，摘要校验是 jigsum -c 的职责（第 17 条断言覆盖），PR 正文与 notes 不得把这条写成"mkimage 具备内容级防篡改"。

## 源码修改

| 补丁 | 改的文件 | 内容 |
|------|----------|------|
| patches/0001-libjte-config-guess-sub-ohos-reanchor.patch | libjte/config.guess, libjte/config.sub | config.guess 加 aarch64:HarmonyOS:*:* -> aarch64-unknown-linux-ohos 分支；config.sub 在 kernel-libc 接受位放行 HarmonyOS/ohos，不改上游判定顺序 |
| patches/0002-libjte-pthread-cancel-teardown-ohos.patch | libjte/checksum.c | 拆除 pthread_cancel() 依赖：改走本文件已有的 quit 标志 + pthread_join 收尾（OHOS musl 无线程取消 API） |
| patches/0003-jigdo-gen-checksum-list-harmonyos-oscase.patch | libjte/bin/jigdo-gen-checksum-list | uname -s 的 case 分支并入 HarmonyOS，使其在 OHOS 上产出 libjte 可接受的十六进制 md5 清单 |

三枚都是 -p1 --dry-run 干净通过的 portability 补丁，已在 conandata.yml 的 patches: 下按 patch_file / patch_description / patch_type 三字段登记。配方自身另有两处非源码改动：mkjigsnap 的 shebang 由 /usr/bin/perl -w 改写为 /usr/bin/env perl，autotools helper 批量补执行位。

## 验证结果

```bash
# B 机（HarmonyOS aarch64）；CONAN_HOME=~/tmp/ch/home-jigit，profile ci/conan/profiles/ohos-aarch64
sh ~/tmp/uc2/z74-jigit/runN.sh create15.log            # 过 build-slot.sh --kind short --mem 2500
#   create15.log: Calling build() 有（test_package 消费者真编译）；CREATE_RC=0
#   SUMMARY jigit consumer: total=29 passed=29 failed=0
python3 scripts/ohc-run.py conan-verify jigit 1.22     # VERIFY_RC=0
```

conan-verify 各节按子行实读（节标题一律显示 PASS，真状态在下一行）：

| 节 | 子行读数 | 是否真做 |
|----|----------|----------|
| G0 | Knowledge hit: E490，另报"已知风险 E490 未在配方中处理" | 命中已核；该告警是扫描器误判——build() 已对 configure/config.guess/config.sub/install-sh/missing/compile/ltmain.sh/depcomp 逐个 chmod +x |
| G1 | 全项 ✅（含补建后的 test_package/MANIFEST.yml 存在） | 是 |
| G2 | conan create 成功，日志 reports/conan-create.log | 是（同 RREV 命中缓存，未重编包体；全量编译证据在 create11–create14 日志） |
| G3 | 无系统同名库冲突（R26 通过） | 是 |
| G4 | ⚠️ 无法找到程序包 ID | 否——产物完整性检查未真正执行 |
| L2 | ⏭️ 跳过（无 cache 路径） | 否——平台功能矩阵未执行 |
| L4 | ⏭️ 跳过（无 cache 路径） | 否——checksec 静态扫描未执行 |
| L5 | ⏭️ 跳过（无 cache 路径） | 否——产物基线对比未执行 |

结论：G0–G3 实做通过，G4/L2/L4/L5 是名义 PASS 空跑，不得当作已验证；根因在 harness 未能从 create 输出里定位 PKGID 对应的 cache 路径，属框架侧问题，本 PR 不改框架。

## 交付物

| 文件 | 大小(B) | 说明 |
|------|---------|------|
| bin/jigdump | 47552 | .jigdo/.template 检视工具 |
| bin/jigit-mkimage | 326144 | 由 .jigdo + .template 重建镜像 |
| bin/jigsum | 39360 | jigdo 22 字符 base64 MD5 清单/校验 |
| bin/jigsum-sha256 | 39360 | 43 字符 base64 SHA-256 清单/校验 |
| bin/parallel-sums | 100864 | 多线程摘要（依赖 pthread） |
| bin/extract-data | 219648 | 从镜像抽取子块 |
| bin/rsyncsum | 35264 | 生成 rsync 贡献块 |
| bin/jigdo-gen-checksum-list | 6339 | 摘要清单生成脚本（#!/bin/sh，补丁 0003） |
| bin/mkjigsnap | 17379 | Perl 快照脚本（shebang 已改写，需 HNP perl） |
| bin/jte-demo | 363136 | 上游 noinst test/demo，模板导出 API 唯一示例驱动 |
| lib/libjte.so.2.0.0 | 354880 | SONAME libjte.so.2（LT 2:0:0），另有 .so/.so.2 软链 |
| lib/libjte.a | 238830 | 静态库（顶层 Makefile 需要 .o，故保留 .a） |
| lib/pkgconfig/libjte-2.pc | - | pkg-config 名 libjte-2 |
| include/libjte/libjte.h | 23734 | 开发头文件 |
| licenses/COPYING, licenses/COPYRIGHT | - | GPL-2.0-or-later / libjte 版权 |
| man/man1/*.1, man/man8/mkjigsnap.8 | - | 7 份 man 页 + jigdo-gen-checksum-list.1 |

## 注意事项
- 版本串按任务串 1.22 申报（libjte 的 AC_INIT 是 2.0.0、SONAME 2 并存，不要"归一化"成 2.0.0）。
- 测试分母 29 的算法：脚本内 `ok "` 站点 20 个，其中 1 个在 10 元素 for 循环里 => 全绿 checks = 20 - 1 + 10 = 29；四处同源=test_jigit.sh 的 SUMMARY 行、test_package/MANIFEST.yml 的 assertion_count、本文件上面三行与验证结果块、manifest.yaml 的 test_results。
- 依赖闭包只有 zlib/1.3.1 与 bzip2/1.0.8（顶层 Makefile 无条件 -lz -lbz2、parallel-sums 另需 -lpthread）；全树无 GTK/GLib/X11/摇杆依赖，台账里"摇杆校准程序"的定性作废。
- 上游无成体系测试（R51 清点：顶层 Makefile 只有 all/lib，libjte 只有 noinst test/demo，add_test 命中 0），故测试全为自建消费者断言。
- ✅ **RREV 两档如实披露（主窗 06:24 一手复算，覆盖此前“单档”结论）**：交付件 `conandata.yml` 的 `url:` 确实只有第 7 行官方 einval 址（无 ghfast/gh-proxy 注入、无 `.ghfast-bak` 遗留），但 **W3 本地 CI 的绿跑并不是在这枚交付件上跑的**：`reports/w3-local-ci.log` 里唯一的导出行是 `Exported: jigit/1.22#6b36e295820ad10ee1d591e0e4494eb1`，同一日志含 1 处 `file:///…/.build-cache/predl_cache/d1b4cce0_jigit-1.22.tar.xz` ⇒ 绿跑当时取的是 harness Pre-download 段改写后的 `file://` 件（修订号 `6b36e295820ad10ee1d591e0e4494eb1`）；交付态 `conan create`/`conan export` 实测 = `50c30c85e4ebe8e551f31effc1b1e757`（PKGID `529476831f2a99ec232a22521c08390fad2c47ea`）。两档不同、不宣称同一 rev；差异面只在 `sources:` 的 url 形态，sha256、`patches:`、`conanfile.py` 与三枚补丁本体逐字未变。
- 载荷小于 1024 B 的 jigdo 闭环里，镜像内容不在 .jigdo 的 [Parts] 而在 template 内联块，消费方要防篡改必须另跑 jigsum -c。

## 已知限制

### 上游 [Parts] 段互通缺口（未修的上游缺陷，与 HarmonyOS 移植无因果关系）

- 同一上游 tarball 内 `jte.c:1275` 写出的是 `name=value` 形式，而 `mkimage.c:535` 读取时要求键名为 `jigdo_name`（必须含 `:`），二者自相矛盾 ⇒ `jigdo_name` 恒 NULL、`[Parts]` 段互通在**上游自身**就不通。
- 该缺口与 HarmonyOS 移植无因果关系，本 PR 未修，只在包内二进制上复现了「[Parts] 为空 / 镜像内容内联 / rc=0 且 cmp 全等」这一形状。
- 复跑状态：独立审计未能二次复跑该条（其 `-m .` 用法错撞进 `mkimage.c:146-169` 的 `malformed match entry`）⇒ 本条按「已知限制 / 未修的上游缺陷」披露，不作「已实测验证的上游 bug 复现」口径。
- 本条为读上游源码所得的行级事实，未做运行级复跑；包内二进制的形状证据见前面「测试前提订正」一节。

---

**编译结束**: 2026-09-27 06:14
**最终状态**: built
