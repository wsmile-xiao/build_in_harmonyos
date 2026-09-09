# E547 — 64 位平台指针截断对齐：以 int 承接 malloc 指针做对齐运算产生非法地址

## 错误特征
- 编译期（clang 15，每处成对 2 条）：`cast to smaller integer type 'int' from 'unsigned char *'` 与 `cast to 'unsigned char *' from smaller integer type 'int'`
- 运行期：消费者程序在 `camAllocateImage` 返回成功后访问 `imageData` 立即 SIGSEGV（实测 exit=139）
- 典型代码（CamelliaLib 2.7.0 `src/cam_utils.c`，8 处同型）：
  `image->imageData=(unsigned char*)(((int)(image->imageDataOrigin-1)/image->align)*image->align+image->align);`

## 触发条件
- 构建系统: 任意（本例 autotools + libtool）
- 阶段: 编译通过（仅有告警）、运行期崩溃（runtime/testing）
- 平台: 64 位目标（aarch64/OHOS；32 位或地址低位恰好对齐时可能侥幸可用）

## 根因分析
2007 年代 C 图像库把 malloc 返回的指针截断为 32 位 `int` 再做整型对齐运算：
`(int)(ptr-1)/align*align+align`。64 位平台上指针高位丢失后：
1. 结果不再是原指针对齐后的等价值（甚至为负数）；
2. 该 int 再被 cast 回指针写入 `imageData`，后续像素访问解引用非法地址。
clue 链：clang `-Wpointer-to-int-cast`/`-Wint-to-pointer-conversion` 告警点与崩溃点一致；
CamelliaLib 2.7.0 全库恰好 8+8 条告警、全部落在 `cam_utils.c` 的 8 处对齐惯用法。

## 解决方案

### 推荐方案
把对齐运算改为 `uintptr_t` 参与整型运算：
`((uintptr_t)(ptr-1)/align*align+align)`，并补 `<stdint.h>`；
32/64 位语义一致、无平台条件宏（R8 合规）。实例：
`patches/0003-src-cam-utils-uintptr-alignment.patch`（camellia/2.7.0）。
补丁后必须以"应用补丁到 pristine 与探索副本 diff -rq 逐字节等价"验证，
源码为 CRLF 时用字节级工具替换，避免 sed 把 `\r` 挪位造成混合换行。

### 禁止做法
- ❌ 用 `-fpermissive`/`-fcommon` 类编译器开关压制告警——不恢复被截断的高位，运行期仍崩
- ❌ 只改"告警点"不改数据流：对齐结果若继续参与指针运算需一并核对宽度
- ❌ 以平台条件宏（`__OHOS__` 等）只对 64 位平台走新代码

## 验证
```bash
make clean && make 2>&1 | grep -c "cast to smaller integer type 'int' from"
# 期望 0；修复前 CamelliaLib 2.7.0 为 8
# 消费者: camAllocateImage + imageData 写读 + 24 项断言 → SMOKE OK (exit=0)
```

## 关联条目
- 相关: E491（legacy autotools 在 HMDFS/OHOS 的加固族——本条目与其互补：E491 管构建期，本条目管 64 位运行期）
