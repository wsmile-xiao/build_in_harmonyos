# syrep 0.9 适配笔记

## 编译环境
- 构建系统: autotools（2005 年代，上游自带 autoconf 2.59 生成的 configure；本适配不重生成，直接修补该 configure）
- 编译日期: 2026-09-25
- 编译器: clang/clang++ (OHOS NDK clang 15, aarch64)
- 状态: built（本地 W3 通过；制品仓 upload 待 PR 合并后 release 流水线执行）

## 编译步骤

syrep 是 CLI 工具（非库），上游 0pointer.de，纯 C + zlib + Berkeley DB：

1. `./configure --prefix=... --disable-lynx`（lynx 为文档渲染工具，CI 无）
2. `make -j1 && make install DESTDIR=staging`
3. 依赖注入：conanfile 用 AutotoolsDeps 把 berkeley-db/zlib 的 -I/-L/-l 送进 configure
4. test_package 实际运行打包出的 syrep 二进制，走 update → makepatch → merge
   端到端往返并断言文件内容一致

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "Berkeley libdb 4.3 required"（4.8.30 被拒） | 上游版本检查硬编码只认 DB 4.3/4.4（2006 年），API 全兼容 4.8 | 补丁放宽为 >= 4.3（configure + configure.ac） |
| 2 | configure: cannot guess build type | config.guess/sub 是 2005 版，不识别 HarmonyOS（uname -s = HarmonyOS） | 补丁：config.guess 增加 HarmonyOS case；config.sub OS 列表加 -ohos* |
| 3 | update 报 "link(): Operation not permitted"，快照无法落盘 | HMDFS 不支持硬链接（知识库 E079） | 补丁：package.c 的 link() 失败（EPERM/EOPNOTSUPP/ENOSYS）时回退 copy |
| 4 | conan create 找不到 db.h | 老式 configure 用 AC_CHECK_HEADER，需要 AutotoolsDeps 注入依赖 -I/-L | conanfile generate() 加 AutotoolsDeps |
| 5 | test_package mktemp 写 /tmp 失败 | /tmp 只读（知识库 E002） | 测试改用 TMPDIR（conanrun 环境指向构建目录） |
| 6 | makepatch 对无快照的仓库失败 | 上游 makepatch 要求双方都有快照 | 测试先对 B 也跑 --update（上游正常行为，非缺陷） |
| 7 | W3 首跑 JC 全仓误报 | 变更未 commit 时 junk_check 落 full 模式，扫出 main 上他人遗留标记文件（cloog/kics） | 先 commit 再 finish（同 vspline 经验） |
| 8 | CI: `./config.status: line 620: ./confLKEcNb/subs1.awk: Permission denied` → `could not setup config files machinery` → `Error in build() method, line 70` | HMDFS + `umask 077` 的 `mktemp -d` 目录恒为 0700，umask 对 HMDFS 目录无效（E110/E112/E129/E011 族）。本地假绿的原因是 PATH 中存在旧任务安装的全局 mktemp 垫片，CI PATH 没有 | 配方内化 mktemp 垫片（`umask 002` + `chmod 2770`），`build()` 以 `PATH="{shim_bin}:$PATH"` 注入 configure/make/install 全链 |
| 9 | W3: `Perl_my_cxt_init: symbol not found`（autoconf 跑不起来） | 系统 autoconf 与 conan perl 混搭；CI 侧同样没有可用的 autotools（E041/E071：CI 不应依赖 autotools 重生成） | 放弃重生成方案：改为直接修补上游 2005 版 configure（补丁 0002，4 行）；`build()` 以 `os.utime` + `AUTOCONF/AUTOHEADER/AUTOMAKE/ACLOCAL=/bin/true` 防止 make 重跑 autotools（E248） |
| 10 | W3: `configure: error: newly created file is older than distributed files!` | 防触发用的 `os.utime` 时间戳写成 `time.time() + 10`（未来时间），触发 autoconf 的系统时钟自检 | 时间戳改为 `time.time()`：不早于依赖文件（configure.ac）且不超前于当前时刻 |

## 源码修改

补丁 5 个（refresh-patch 按文件切分）：
- 0001-config.guess.patch — 识别 HarmonyOS
- 0002-configure.patch — 上游 2005 版 configure 的 DB 版本守卫放宽（4 行；替代旧的 14805 行整文件重生成补丁 0004）
- 0003-config.sub.patch — 接受 ohos triple
- 0005-configure.ac.patch — 版本检查放宽源头
- 0006-src-package.c.patch — link() HMDFS 回退 copy（E079）

> 不再携带 configure/config.h.in 的整文件重生成补丁：CI 无 autotools 工具链（见问题 9），
> 且 14805 行 diff 无法评审（R52/R6）。configure 除该守卫外与上游 tarball 逐字节一致。

## 依赖版本

- berkeley-db/4.8.30（制品仓已发布）
- zlib/1.3.1（制品仓已发布）

## 验证结果

```bash
conan create archives/s/syrep/0.9 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 结果: PASS（677 行日志；ERROR=0 / Error in=0 / Permission denied=0）
# 上游测试: [upstream test 1/2] copy-fd-test PASS (65792 bytes, sha256 match)
#           [upstream test 2/2] rm-rf-test PASS (nested tree removed)          → 2/2
# test_package: ./test_syrep → "syrep 0.9 test passed: update/makepatch/merge round-trip OK" → 7/7
# 二进制自报链接: Compiled with libdb 4.8.30, linked to libdb 4.8.30（静态链入自建依赖，R26 生效）
```
> **注意**：本地复验必须用 CI 同款 profile（默认 profile 缺 `settings.os.version` → RC=6）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/syrep | ~1.3MB | CLI 工具（aarch64 OHOS ELF） |

## 注意事项

- syrep 为 **application 包**（R38）：commands.json 已声明（tool 类型）
- berkeley-db 只发静态库（libdb.a），链接进 syrep 二进制，无运行时 .so 依赖
- 上游 2 个测试程序（src/copy-fd-test.c、rm-rf-test.c）未被上游注册进 TESTS，
  本适配在 `build()` 内接入自动执行并实测 **2/2 PASS**，test_package/MANIFEST.yml 已按 R51 申报
- merge 命令遇同名文件会交互式询问（上游正常行为），脚本场景注意 stdin
---

**编译结束**: 2026-09-25（W3 复验 v4 全绿：conan create PASS / 上游 2/2 / test_package 7/7）
**最终状态**: built（#12742 重推后由 CI 复核）
