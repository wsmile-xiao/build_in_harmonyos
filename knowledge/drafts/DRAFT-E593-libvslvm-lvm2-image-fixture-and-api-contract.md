# DRAFT-E593 — 合成合法 LVM2 物理卷镜像做 libvslvm 消费者测试的最小口径与 libvslvm 公共 API 契约

> 草稿（DRAFT，编号 E593）。与同目录 `DRAFT-E593-libvslvm-lvm2-image-fixture-and-api-contract.kv` 成对。
> 取号说明：`knowledge_id.py --claim/--check` 在本机假阴性报 E584 空闲（该号实为并行任务
> libbfio 的 `DRAFT-E584-libyal-tests-prefix-and-driven-subset`，worktree 内实物存在），
> E585 亦已被 libgmpxx 任务占用并写进其 manifest。改用三面人工复核定 E593：
> ①文件面：全工作区（含 `worktrees/*/knowledge/drafts/`、主检出）无 E593 文件名；
> ②上游主线整词面：`git grep -nE '(^|[^0-9A-Za-z_#/:-])E593([^0-9]|$)' upstream/main -- knowledge/` rc=1 无命中；
> ③引用面：各 worktree `knowledge/` 与 `archives/**/manifest.yaml` 无 E593 整词引用。
> 该工具缺陷与 `2026-09-19-orchestrator-knowledge-id-false-negative.md`、libgmpxx 审计记录同源。

## 来源

任务 `feat/libvslvm-20240504`（libvslvm 20240504，libyal Linux LVM2 卷系统访问库，
HarmonyOS PC 积分赛新增包）。消费者测试需要在设备上合成一个**合法的** LVM2 物理卷镜像，
再走公共 API 读回；合成过程中 libvslvm 的四处专属约定逐一暴露，全部经设备原生构建实测
（`$TASK_DIR/native-probe.sh`，21+31 项断言）确认。

## 四处夹具专属约定（逐条实测）

| # | 约定 | 实测现象（误配时） | 正确做法 |
|---|------|--------------------|----------|
| 1 | 标签探测位置割裂 | 标签放扇区 0：`check_volume_signature` 返回 0（它只读**固定偏移 512**），但 handle open 能扫到——「签名查不到、打开可行」的矛盾态 | 标签放**扇区 1**（LVM2 pvcreate 默认 labelsector=1），两路都过 |
| 2 | raw location descriptor 偏移为**元数据区相对偏移** | 写绝对偏移 4608：解析器存 `file_offset+offset`=8704，读回全零页 → `mismatch in checksum (… != 0x45403080)`（17 字节全零的 CRC） | descriptor offset 写 `4608-4096=512`（相对区头） |
| 3 | 元数据文本 id 必须 38 字符连字符 UUID | 32 字符裸串：`libvslvm_volume_group_set_identifier: identifier size value out of bounds`（解析器要求 `identifier_size == 39` 含终止符） | 6-4-4-4-4-4-6 共 38 字符，如 `AbCdEf-GhIj-KlMn-OpQr-StUv-WxYz-012345` |
| 4 | extent_size 解析后 ×512 存储 | 断言 `get_extent_size()==8192` 失败，实测返回 4194304 = 8192×512；段 offset/size 同样按存储值换算 | 断言按 `8192×512` 写，或夹具元数据写 `extent_size = 16` 这类小值 |

另有两个**排障时极易绕远**的结构事实：

- 元数据区头 512 字节：**校验和在 +0**（覆盖 +4..+512）、签名 ` LVM2 x[5A%r0N*>` 在 +4、
  version 在 +20、raw location descriptor 在 +40（24 字节 ×N，全零项终止，最多扫 4 条，
  open 路径要求恰 1 条非忽略项）。若把头校验和误写到 +4 会**覆盖签名前 4 字节**，
  报 `unsupported metadata area signature`（本项目实测踩中）。
- 标签头校验和为 weak CRC32（初值 `0xf597a6cf`、多项式 `0xEDB88320`、无终 XOR），
  范围 `+20..+512`，且必须在**该扇区其余字段全部写完之后**计算——先算后写会让
  pv_header/描述符区以全零参与 CRC，报 `mismatch in checksum`（本项目实测踩中）。

## libvslvm 公共 API 契约（消费者断言口径）

| API | 成功返回 | 备注 |
|-----|----------|------|
| `libvslvm_handle_initialize` / 各 getter / `set_codepage` / `get_codepage` | **1** | libyal 惯例，不是 0 |
| `libvslvm_handle_close` | **0** | 对**未打开**的句柄返回 **-1**（按设计） |
| `libvslvm_handle_free` | **1** | 与 close 不同 |
| `libvslvm_check_volume_signature` | 1 找到 / 0 未找到 / -1 错误 | 只探测偏移 512 |
| `libvslvm_error_sprint` | 只打**最外层**帧 | 空白卷打开的最外层文案是 `unable to open handle: …`；内层 `unsupported number of metadata area descriptors: 0.` 要用 `libvslvm_error_backtrace_fprint` 才可见 |
| `libvslvm_logical_volume_read_chunk_data` | （内部 API） | 入参为 libfdata vector 内部对象；消费者可达的最深链路是**签名→打开→卷组→物理卷→逻辑卷→段→条带**的元数据链 |

卷组里的物理卷对象来自**元数据文本**（`physical_volumes { pv0 { … } }` 段），
label 上的数据区/元数据区描述符**不会**出现在它身上（实测
`get_number_of_*_area_descriptors == 0`）；label 的 pv_header 32 字节标识符与文本 id
（38 字符）是两个独立字段。

## 设备复现

```sh
sh "$HOME/tmp/libvslvm-20240504/native-probe.sh"
# 预期：configure rc=0；make rc=0；vslvminfo/vslvmmount -V rc=0；
# make check → TOTAL 3 / PASS 2 / SKIP 1；
# test_libvslvm 21 项断言 0 失败；test_ohos 31 项断言 0 失败（含 LVM2 镜像读回全链路）
```

定稿形态见仓库内 `archives/l/libvslvm/20240504/test_package/`（`test_ohos.c` 即该夹具）。

## 与既有条目的边界

- E591：GPT 合成镜像（保护性 MBR/主备头/entries/CRC-32）与三元组年代——卷系统格式不同，
  三层结构不重叠。
- E584：libyal 上游测试的 TESTS/check_PROGRAMS 清点口径——本包 N=23 同构适用，但内容是
  测试清点而非镜像夹具。
- E011：configure umask 077→022——本包构建期同样命中，但机制不复述，仅关联。
