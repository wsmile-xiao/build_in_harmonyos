# DRAFT-E726：libvmdk 合成 monolithicFlat VMDK 夹具三坑（规范 camelCase / 显式 extent 打开 / set_max 调用序）

> Status: **Draft**（待审核 promote）| severity: `2` | category: `api|upstream-bug|consumer-test` | Updated: 2026-09-25
> 对应: `knowledge/drafts/DRAFT-E726-libvmdk-monolithicflat-fixture-and-setmax-pool-quirks.kv`
> 来源: libvmdk 20240510 适配（libyal/libvmdk @ tag 20240510, 34890e3d）——消费者测试合成夹具取证
> 取号: `knowledge_id.py --claim --task libvmdk-20240510` → E726（三面并集回查未占用）

---

**匹配关键词**：libvmdk, monolithicFlat, monolithic flat, createType, extent data file IO pool, unsupported disk type, set_maximum_number_of_open_handles, last used list element, VMDK 夹具, open_extent_data_files, disk_type UNDEFINED

## 错误签名（error_signature）

```text
missing extent data file IO pool|unsupported disk type|unable to set maximum number of open handles in extent data file IO pool|libbfio_internal_pool_close: unable to retrieve value from last used list element
```

## 预扫（prescan）

- `prescan_pattern`: `createType.*monolithic flat|libvmdk_handle_set_maximum_number_of_open_handles|RW .* FLAT `
- `prescan_globs`: `*.c, test_package/*.c, tests/*`
- `prescan_severity`: 2

## 根因（root_cause）

三条独立的上游语义（libvmdk 20240510 设备探针 2026-09-25 实测）：

1. **createType 按 value_length 分支匹配，只认规范 camelCase**：`libvmdk_descriptor_file.c` 对 createType 的值逐长度分支比较（14 字符分支 = `monolithicFlat`、16 字符分支 = `2GbMaxExtentFlat`/`monolithicSparse`/`vmfs*`）。VMware 风格带空格的 `monolithic flat`（16 字符）**不在任何分支** → `disk_type` 留 UNDEFINED(0)。元数据解析不受影响（media size/CID 照常成功），但读路径的 `libvmdk_extent_table_initialize_extents()` 对 UNDEFINED 走拒绝分支 → `unsupported disk type`——**「元数据全绿 + 一读就错」的分裂形态**。
2. **monolithic flat 的 extent 数据文件不会被 handle_open 自动打开**：数据在独立 flat 文件里，handle_open 只打开 descriptor；extent data file IO pool 为 NULL → 一切 read/seek 报 `invalid handle - missing extent data file IO pool`。必须显式调用 `libvmdk_handle_open_extent_data_files()`（monolithic sparse 数据与 descriptor 同文件的场景才免）。media size 可读不代表数据面已就绪。
3. **set_maximum_number_of_open_handles 只能在 pool 未建（open 前）调用**：pool==NULL 时返回 1；pool 已建时 libvmdk→libbfio 包装把 libbfio 的成功返回当失败（`!= -1` 条件分支把 1 判成异常），恒返 -1 且 libbfio 侧对 last-used list 的清理把元素 value 置空 → 后续 `handle_close` 的 pool_close_all 报 `unable to retrieve value from last used list element` 连带失败——**一次错误调用同时污染两个 API**（上游缺陷，不改上游源码，调用序规避）。

## 推荐方案（rec_approach: `spec-camelcase-fixture + explicit-extent-open + setmax-before-open`）

自造 VMDK 夹具 / 消费者测试三步走（libvmdk 20240510 实测 41+31 断言全 PASS 的姿势）：

1. 描述文件按 VMDK 规范写 camelCase：`createType="monolithicFlat"`，附 version/CID/parentCID、`# Extent description` 段与 `RW <扇区数> FLAT "<数据文件名>" 0` 行；数据文件 = 扇区数×512 字节的裸 flat 镜像；
2. `libvmdk_handle_open(descriptor)` 成功后**立刻** `libvmdk_handle_open_extent_data_files()`，再取 media size / disk type / CID 并读数据；
3. `libvmdk_handle_set_maximum_number_of_open_handles()` 放在 handle_initialize 之后、handle_open 之前。

断言语义一并钉死（同轮探针实测）：disk type=`LIBVMDK_DISK_TYPE_MONOLITHIC_FLAT`、CID=`0xfffffffe`、parentCID 返回 1 且值 `0xffffffff`、读到 EOF 返 0 字节且不置错、handle_close 成功返 0、签名探测对 descriptor 文本返 1 / flat 数据文件返 0 / 缺失文件返 -1+error。

## 证据（evidence，逐字）

负证（probe.c，spaced `monolithic flat`）：

```text
PROBE disk_type rc=1 value=0
PROBE open_extent_data_files=-1
PROBE extent_error=libvmdk_extent_table_initialize_extents: unsupported disk type.
PROBE read_full count=-1 match=0
（另一形态：libvmdk_handle_read_buffer: invalid handle - missing extent data file IO pool.）
```

正证（probe2.c，camelCase + 显式 extent 打开）：

```text
open_extent_data_files=1
read_512_after=512 match=1
read_8192_after=7680   # 此前已读 512，余量 8192-512=7680，语义自洽
```

set_max 四变体（probe3.c）：

```text
variant A: set_max(4) = -1 "unable to set maximum number of open handles in extent data file IO pool."
           随后 handle_close = -1 "libcdata_list_element_get_value: invalid list element."
variant B: set_max(32) = -1（与取值无关，恒失败）
variant C: open 前 set_max(4) = 1（no error）
variant D: 对照组 signal_abort=1 close=0
```

交付面：`test_package/test_libvmdk.c` 41/41、`test_ohos.c` 31/31 全 PASS（原生树实跑 + conan create 干净轮一致），上游 `make check` FAIL 0。

## 复现命令（verification_cmd，设备可直接执行）

```sh
TD=$HOME/tmp/libvmdk-20240510; SRC=$TD/native-src
export LD_LIBRARY_PATH=$SRC/libvmdk/.libs
cd $TD
clang probe.c  -I$SRC/include -L$SRC/libvmdk/.libs -lvmdk -o probe  && ./probe   # 负证三签名
clang probe2.c -I$SRC/include -L$SRC/libvmdk/.libs -lvmdk -o probe2 && ./probe2  # 正证读通
clang probe3.c -I$SRC/include -L$SRC/libvmdk/.libs -lvmdk -o probe3 && ./probe3  # set_max 变体
```

## 源码依据

- `libvmdk/libvmdk_descriptor_file.c`：createType 长度分支（14=`monolithicFlat`、16 分支无 spaced 项）
- `libvmdk/libvmdk_extent_table.c`：`initialize_extents` 的 disk_type 白名单拒绝 UNDEFINED
- `libvmdk/libvmdk_handle.c`：`set_maximum_number_of_open_handles` 的 `!= -1` 分支（成功返回被判失败）

## 适用范围与边界

- **适用**：任何对 libvmdk 做消费者测试 / 自造 VMDK 夹具的适配；libyal 同型 API 形态需逐包核对。
- **边界**：真实上游发行的 VMDK 文件本身用规范 camelCase，不受影响；本条只针对自造夹具写错形态与 API 调用序；monolithic sparse（单文件）场景不需要显式 extent 打开。

## 关系

- **similar_to**：E586（libyal 家族假信号族）、DRAFT-E591（同族 libvsgpt 夹具与三元组）
- **caused_by**：上游 descriptor 解析器的长度分支设计 + extent IO pool 惰性打开 + set_max 包装条件写反
- **prerequisite_of**：libvmdk 任何端到端夹具 / 上游 tests/input 类夹具生成器
- **conflicts_with**：无

---

*本文件由 `knowledge/drafts/DRAFT-E726-libvmdk-monolithicflat-fixture-and-setmax-pool-quirks.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
