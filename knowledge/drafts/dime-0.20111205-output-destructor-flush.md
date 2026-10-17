# dimeOutput 析构才 flush（同进程写读回环的 0 字节陷阱）

> Draft: DIME-OUTPUT-DESTRUCTOR-FLUSH
> Stem: `dime-0.20111205-output-destructor-flush` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DIME-OUTPUT-DESTRUCTOR-FLUSH
- **严重度**: 3
- **类别**: api-semantics
- **触发工具**: none（库 API 语义）
- **阶段**: consumer-test

## 错误特征

```
RUN: ./test_dime
FAIL: input file opened        # 对应 CHECK(in.setFile("smoke.dxf"), ...)
```

写阶段两个断言（`out.setFilename` 与 `model.write(&out)`）都通过了，
读回 `dimeInput::setFile` 却失败——报错形似"打不开文件"。

## 可复现问题

同一个测试程序里：

```cpp
dimeOutput out;
out.setFilename("smoke.dxf");
model.write(&out);            // 返回 true
dimeInput in;
in.setFile("smoke.dxf");      // 返回 false！
```

在 `model.write()` 之后、`setFile` 之前 `ls -l smoke.dxf` 可见文件为
**0 字节**。（真机 HarmonyOS 上实证；任何用 libc stdio 缓冲的平台同理。）

## 根因分析

1. `dimeOutput::setFilename()` 只 `fopen(filename, "wb")`，数据写入
   stdio 缓冲；`dimeModel::write()` 返回 true 仅代表数据进了缓冲。
2. **flush 和 fclose 都发生在 `~dimeOutput()`**，库没有公开的
   close()/flush() 方法。
3. `dimeInput::setFile()` → `setFilePointer()` 用
   `lseek(fd, 0, SEEK_END)` 的结果，以 `filesize > 0` 为成功条件——
   0 字节文件直接判失败。

上游示例（dxfsphere）写完就退出进程、析构随进程结束自然发生，所以
上游从未暴露此坑；**同进程写读回环**的消费者测试必踩。

## 解决方案

**主方案**: scope-block-before-readback

```cpp
{
  dimeOutput out;
  CHECK(out.setFilename("smoke.dxf"), "output file opened");
  CHECK(model.write(&out), "model written to DXF");
}  // ~dimeOutput flush + fclose，文件落盘
dimeInput in;
CHECK(in.setFile("smoke.dxf"), "input file opened");
```

写读回环测试建议：失败信息里带上文件大小（`stat`/`ls -l`），
以便快速区分本坑与真实的文件系统/权限问题。
