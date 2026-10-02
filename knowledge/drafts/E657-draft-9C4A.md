# DRAFT: 镜像级文件系统工具（UDF toolkit）在 OHOS 的“无挂载闭环”验证模式

- **草稿 ID**: E657（E657-draft-9C4A）
- **来源库**: udfclient 0.8.21（newfs_udf / udfdump / udfclient；OHOS PC aarch64）
- **状态**: 草稿（待主编 promote 为正式 E 条目）
- **源 PR**: #13235（路径 A+B）

## 现象（真机实测）

1. **文件镜像必须显式扇区大小**。`newfs_udf -L TESTVOL -b 2048 -s 8192 test.udf` 创建 16 MiB 镜像后：

   - 不传 `-b` 时挂载路径找不到卷集（alive sets 为空）：

     ```
     UDF volume sets marked alive :
     ```

   - 显式 `-b 2048` 后同一镜像正常：

     ```
     Volume set `6ab8b6d359ecbb83` (1 volume) with 1 partition
         ... contains logical volume  `TESTVOL`
     ```

   - `udfdump -S`（顺序描述符扫描）始终可读到 `Logical volume id `TESTVOL`` —— 证明镜像结构正确，
     差异在挂载路径的扇区推断。

2. **镜像写路径依赖介质语义**：`printf 'mkdir HELLO\n...' | udfclient -b 2048 -W test.udf` 在文件镜像上
   返回 `Can't determine directory the new directory needs to be created in 0 </> </HELLO> </>`，
   且 `sector written 0`（真实光盘介质不在本边界内）。

## 根因

- 工具默认按光盘介质推断扇区大小；普通文件镜像无介质信息，需显式 `-b <sectorsize>`（与镜像创建时一致）；
- 写路径（mkdir/put）依赖可写介质语义，上游对纯文件镜像的写支持不完整（不落盘、报目录定位错误）；
- SCSI 工具（cd_disect / mmc_format）依赖 `/dev/sr*` 等设备路径，镜像沙箱内不可验证。

## 处理方式（消费者测试模式）

`test_package/test.sh`（13 项断言）实现“无挂载、无特权”闭环：

```bash
newfs_udf -L OHOSTESTVOL -b 2048 -s 8192 consumer.img          # 建镜像
udfdump -S consumer.img | grep -q OHOSTESTVOL                  # 顺序扫描（结构）
udfdump -b 2048 consumer.img | grep -q "Volume set"            # 挂载（卷集）
udfdump -b 2048 -t consumer.img | grep -q "Directory tree of mount point"
printf 'ls\nexit\n' | udfclient -b 2048 consumer.img | grep -q "Directory listing of /"
```

要点：断言按“输出写文件 + grep 文件”实现——大输出（`udfdump -S` 约 600 KiB）直接管道给 `grep -q` 会在
`set -o pipefail` 下因 SIGPIPE(141) 假失败；且 >128 KiB 输出作为单参数会触发 E2BIG（本 PR 两轮实测）。

## 适用范围与边界

- **适用**：对普通文件创建/读取文件系统镜像的用户态工具（UDF/ISO 等）的适配与消费者测试；
  设备相关的介质层工具（SCSI/CD）应按“构建 + 用法”最小验证并如实标注边界。
- **边界（查重）**：与 E421（下载源不可达）无关；与 FUSE/内核挂载类适配（mhddfs 等）不同——本模式
  **不需要内核挂载**，全部在用户态完成；与常规光盘读写/刻录知识不重叠，本条聚焦**镜像文件路径**。
- 未验证边界如实申报：真实光盘读写、SCSI 工具介质路径。

## 验证

```bash
python3 scripts/ohc-run.py conan-verify udfclient 0.8.21 --profile ohos-aarch64-device
# → G0-G4 PASS + test_package 13/13 断言
```

## 关联

- 相关: E002（TMPDIR 只读）、E074（make 并发）；DRAFT-mhddfs-0.1.39.0-ohos-fuse-consumer-mount-boundary（FUSE 挂载边界，不同路径）
