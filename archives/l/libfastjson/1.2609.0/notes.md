# libfastjson 1.2609.0 — 适配笔记

> 档案创建时间: 2026-09-10
> 状态: built（本地 conan create 全绿，待 CI）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libfastjson |
| 版本 | 1.2609.0（上游 2026-09 最新 tag） |
| 构建系统 | autotools（release tarball 自带 configure） |
| 编译器 | clang |
| 源码 | libfastjson-1.2609.0.tar.gz（GitHub 官方 release） |
| sha256 | 7cd6f78c1c07f4140f6976a9a0e0048bcaa7292329c6ac2c0e070383d83d8edd |
| 依赖 | 无（libfastjson 本体零外部依赖） |

## 二、与 1.2304.0 底稿的关系

以 `archives/l/libfastjson/1.2304.0/`（manifest+notes+patches，无 conanfile）为底稿：
- 1.2304.0 完成过 autotools 构建验证 + make check 17 项 PASS（staging 验证后中断，配方未写）。
- 1.2609.0 官方 release tarball **自带完整构建文件**（1.2304.0 时代为 0 字节空文件——上游已修复发行问题），
  故 conanfile 走 `configure + make` 主线，无需 autoreconf（libestr 的 archive-tarball 模式不需要）。
- 1.2304.0 的 0001/0002 补丁是「空文件→OHOS-aware 完整文件」形态，对 1.2609.0 **不适用**
  （dry-run 实测 `patch does not apply`）；本版重新生成为**最小增量补丁**（+22/+33 行，
  符合仓库 acpitool/adplug 等惯例）。

## 三、适配过程

### Phase 1: 源码获取与补丁核验
- [x] 官方 release tarball 下载（GitHub releases，448KB）
- [x] 实测 1.2609.0 自带 config.guess（2022-01-09 版）在本机报
  `unable to guess system type` → 确认仍需平台补丁
- [x] 0001-config.guess.patch：case 表插入 `*:HarmonyOS:*:*` 分支 → 实测输出
  `aarch64-unknown-linux-ohos`
- [x] 0002-config.sub.patch：三处最小增量（ohos-linux 解析分支 + `ohos*` 基本系统类型 +
  `linux-ohos*` kernel-os 组合）→ 实测接受 `aarch64-unknown-linux-ohos`
- [x] 两补丁 `git apply` dry-run 双重验证通过

### Phase 2: conan create（ohos-aarch64 profile）
- [x] 第 1 次失败：conandata 误用 archive tarball（无构建文件，补丁无处应用）→ 改用 release tarball
- [x] 第 2 次失败：**E046 HMDFS umask 077**——config.status 报
  `./confXXXXXX/subs1.awk: Permission denied` → 加 sed workaround
  （`umask 077 && mktemp → umask 000 && mktemp`，libestr 0.1.11 同款先例）
- [x] 第 3 次失败：21/22 PASS，**test_dump_buffered 失败**——上游测试用 `tmpfile()`
  写文件，OHOS /tmp 只读（root filesystem），实测 `tmpfile() = 0, Permission denied`，
  且 TMPDIR 无效（平台限制，非源码 bug）→ 0003 补丁改为**运行时 feature detection**
  （探测 tmpfile() 可用性，不可用则跳过 file-write 段；POSIX 兼容方式，无平台宏——
  符合 review-memory R8 首选方案；in-memory 段仍跑）
- [x] 第 4 次**全绿**：22/22 PASS + test_package round-trip OK

### Phase 3: 测试结果（make check 进 build()）
上游 tests/Makefile.am 注册 **22 个测试目标**（1.2304.0 为 17 个，1.2609.0 新增 5 个）：

```
# TOTAL: 22
# PASS:  22
# SKIP:  0
# FAIL:  0
```

全清单：ucs_copyright_char / test_float / test_dump_buffered* / test_json_util /
test_array_api / test_fuzz_parser / test_fuzz_serializer / test1（含 Formatted 变体）/
test2（含变体）/ test4 / testReplaceExisting / test_parse_int64 / test_cast /
test_parse / test_locale / test_charcase / test_printbuf / test_obj_iter-del /
test_object_object_add_ex（含变体）/ test_many_subobj / test_obj_obj_get_ex-null /
chk_version

*test_dump_buffered 的 file-write 检查段在 OHOS 上平台限制豁免（0003 补丁，
tmpfile() 只读 /tmp），内存缓冲输出段正常执行且 PASS。

### Phase 4: test_package（消费者视角）
- test.c：fjson_tokener_parse 解析 → 4 字段类型断言（string/int/double/bool）→
  序列化重解析 round-trip → 程序化构建对象再 round-trip
- 编译链接 `-lfastjson` 直接 clang 调用（libestr 同款模式，规避 E046 的 CMake find_library 问题）
- 实测输出：`libfastjson version: 1.2609.0` / `test libfastjson 1.2609.0: OK (parse + typed access + round-trip)`

## 四、踩坑记录

| # | 问题 | 原因 | 解决 |
|---|------|------|------|
| 1 | 1.2304.0 补丁 0001/0002 不适用 | 旧补丁是"空→整文件"形态，1.2609.0 文件非空 | 重新生成最小增量补丁（+22/+33 行） |
| 2 | config.status: confXXXXXX/subs1.awk Permission denied | E046 HMDFS umask 077 | sed 改 umask 000（libestr 先例） |
| 3 | test_dump_buffered: file != NULL 断言失败 | OHOS /tmp 只读，tmpfile() 恒失败（TMPDIR 无效） | 0003 运行时 feature detection 跳过 file-write 段（POSIX 兼容，无平台宏），notes+报告定性 |

## 五、版本背景

- 本版与 goblinrs 的 #4771（1.2304.0）**不冲突**：上游同库多版本并存口径，
  制品仓此前无 libfastjson 任何版本，本版为首个可发布配方。
- 平台任务 #7196；下游 rsyslog 链（#8332 rsyslog-cisco 等）依赖本包发布。
---

**编译结束**: 2026-09-10 14:16
**最终状态**: published
