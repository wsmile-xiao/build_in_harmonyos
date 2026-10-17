# E735: libslz 的 slz_adler32_* 是裸累加器，Adler-32 初值必须显式传 1

> Draft: `DRAFT-E735-libslz-adler32-init-value`
> 来源：libslz/1.2.1 适配（test_package 消费者断言），2026-09-25

## 现象

libslz 1.2.1 的 `test_package` 里用库自身的 `slz_adler32_by1()` 去复算 zlib 封套
尾部的 Adler-32，断言写成与 CRC32 一样的初值 `0`，两条断言失败：

```text
ASSERT_FAIL zlib_adler32_trailer
ASSERT_FAIL adler32_vector_123456789
```

实测：`slz_adler32_by1(0, "123456789", 9) = 0x091501DD`，
而标准值 `zlib.adler32(b"123456789") = 0x091E01DE`。
**同一段代码里的 CRC32 断言却用初值 `0` 是对的**
（`slz_crc32_by1(0, "123456789", 9) = 0xCBF43926` = `zlib.crc32`）。

## 根因

`slz_adler32_by1/adler32_by4` 是**裸累加器**：把入参 `adler` 当作已累积值继续加，
不做 Adler-32 规范的初值归一化（规范初值 a=1, b=0 即 `0x00000001`，zlib 内部以 1 起算，
libslz 写 zlib 封套尾部时同样以 1 起算）。传 0 起算导致 a 项少 1、b 项按错位的 a 累加，
最终差 0x8D03——形态是「差一点点的校验和」，容易被误判成端序写反或 trailer 偏移错一位。

两个校验函数的初值约定**不同**：CRC32 初值 0、Adler-32 初值 1。

## 判定方法（可机器匹配）

```bash
# 三方比对：本库 0 档 / 本库 1 档 / 独立标准实现
clang -O1 -I <libslz-build> -I <libslz-src> probe.c <libslz-build>/libslz.a -o probe && ./probe
python3 -c "import zlib;print('zlib=%08X'%(zlib.adler32(b'123456789')&0xffffffff))"
```

`by1(1)` 与 `zlib.adler32` 逐字相同、`by1(0)` 不同 → 命中本模式（不是端序/偏移问题）。

## 处置建议

- 断言侧一律写 `slz_adler32_by1(1, buf, len)`；**不改上游源码、不打补丁**
  （这是合法的累加器 API 语义，只是调用方要传对初值）。
- 自证闭环：libslz 写进 zlib 封套尾部的 4 字节 BE adler 必须等于
  `slz_adler32_by1(1, ...)`，且独立解码器（python zlib）校验通过。
- 写任何 `*32` 校验和断言前，先做一次初值 0 与 1 的对照打印，不要假定所有函数初值约定相同。

## 实例数据

- libslz/1.2.1 `test_package`：`zlib_adler32_trailer`、`adler32_vector_123456789`
  两条断言按初值 1 修正后 31/31 全绿；round-trip 由 python zlib（独立实现）交叉验证。

## 降级方案（fallback）

- 若目标库确实要求 0 起算（个别自实现）：以「库自己写进封套的值」反推初值，
  不以标准值硬套；三方比对未对齐前不得把断言失败写成 PASS，如实记失败并留初值对照表。

## 复现命令

```bash
# 落 $TASK_DIR（见 .kv 的 verify_cmd，设备可直接执行）
"$HOME/tmp/libslz-1.2.1/probe"
# 期望: by1(0)=091501DD  by1(1)=091E01DE  crc(0)=CBF43926
```
