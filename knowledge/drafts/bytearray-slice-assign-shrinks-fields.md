# `bytearray` 切片赋值长度不足会整体左移 —— tarfile 只报 `invalid header`，不会说"你的字段短了 1 字节`
> Draft: `DRAFT-BYTEARRAY-SLICE-ASSIGN-SHRINKS-FIELDS`
> Stem: `bytearray-slice-assign-shrinks-fields` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-BYTEARRAY-SLICE-ASSIGN-SHRINKS-FIELDS
- **严重性**: 2
- **类别**: testing|python|portability
- **触发工具**: python3|test
- **阶段**: testing

## 错误特征

在 Python 里逐字节复刻一个 C 程序手写的定长二进制结构（典型：tar 的 512 字节头），
写完用标准 reader 打开，得到的是：

```
tarfile.ReadError: file could not be opened successfully:
- method gz: ReadError('not a gzip file')
- method bz2: ReadError('not a bzip2 file')
- method xz: ReadError('not a lzma file')
- method tar: ReadError('invalid header')
```

调试时逐字段 dump 会看到更早的征兆：

```
mine chksum: b'0006107\x00'     # 校验和字段后面没有空格了
mine type  : b'\x00'            # 156 处的 typeflag 变成了 NUL
```

## 根因

C 的写法**永远原地写入固定宽度**：

```c
sprintf(header + 124, "%011o", size);   /* 12 字节字段：11 位八进制 + NUL */
sprintf(header + 148, "        %1d", type);  /* 8 空格 + 1 位类型符，落在 148..156 */
sprintf(header + 148, "%06o", sum);     /* 6 位 + NUL，落在 148..154 */
```

Python 的切片赋值语义完全不同 —— `hdr[124:136] = <11 字节>` 等价于
"**删掉这 7 个字节，再插入 11 个**"：`bytearray` 整体从 512 缩到 511，
**156 处的 typeflag 及其后所有字段整体前移一位**。代码读起来毫无异常，
也没有任何"长度不对"的报错，只有下游 reader 抛 `invalid header`。

同源的第二个错误：把校验和写成 `sum % 4096`（以为八进制字段会自动截断），
而 C 的 `sprintf("%06o", sum)` 在超过 6 位时是**照抄全部位数**，不截断。

## 影响范围

- 所有"用 Python 重写或校验 C 生成的二进制结构"的场景：tar/zip 归档合成、固件镜像、
  ELF 头解析、协议帧构造、bootloader 校验脚本
- 特征是"先按固定偏移逐字段填值 → 再交给标准 reader 验证"，且偏移表来自 C 源码而非 Python 库

## 影响范围之外的好消息

`calc_chksums` 只要求"把校验和字段当 8 个空格"求和等于存值，
所以只要 148..155 这 8 个字节在求和瞬间是空格，写成几位的八进制都能被读出来——
**校验和位数不是问题，字段位移才是**。反过来，位移一定会破坏 156 的 typeflag。

## 推荐方案

**方法**: `fixed-width-writer-with-assert-len`

1. 不要裸写切片赋值，统一走定宽写入器，写完立即断言总长：

```python
def put(hdr, offset, width, value):
    field = value.ljust(width, b"\0")[:width]   # 或 struct.pack_into
    hdr[offset:offset + width] = field
...
put(hdr, 124, 12, size)
put(hdr, 148, 7, sum(hdr))     # 第 8 字节保留占位空格
assert len(hdr) == 512
```

2. 先做一次"空 buf 全字段写入"自检，把每个字段起止偏移打印出来，与 C 源码逐个对齐，再填真实数据。
3. 校验和按 C 的真实语义算，**不取模、不截断**。
4. 最省事的兜底是拿真产物当 ground truth：宿主 gcc 编译同一个 `.c` 生成真实归档，
   dump 前两个 512 字节头与自写版本逐字段比对。

## 验证命令

```bash
python3 -c "h=bytearray(512);h[124:136]=b'0'*11;print(len(h),repr(h[156:157]))"
# 错: 511 b'\x00'      ← 长度变了，typeflag 位移
python3 -c "
h=bytearray(512); h[124:136]=b'0'*11
print(len(h), repr(h[156:157]))"   # 对照写法：先 ljust 到 12 字节
```

## 取证记录

- 包：smem 1.5（`archives/s/smem/1.5`），`test_package/test_smem.py` 复刻 `smemcap.c:writeheader()`
- 真实 ground truth：宿主 gcc 编译同一 `smemcap.c` 生成 3013632 字节采集归档，
  Python `tarfile` 可正常打开（262 成员），据此确认字段偏移与校验和算法
- 逐字证据：`archives/s/smem/1.5/notes.md`（问题 #6）