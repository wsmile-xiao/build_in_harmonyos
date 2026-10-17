# DRAFT-13533：鸿蒙 musl open_memstream 在 fclose 前未 fflush 时丢数据

## 现象
上游 lsquic 测试 `test_hcsi_reader` 断言失败：期望的回调输出（经
`open_memstream` 收集）为空字符串。全部 read_sz 组合（1..N）皆空。

## 根因
鸿蒙 PC musl 的 `open_memstream`：**fprintf 后不 fflush 直接 fclose，
最终 buffer 丢失**（sz=0）。POSIX 要求 fclose 隐式 flush；glibc 与
上游 musl 正常，鸿蒙 musl 实现有缺陷。

## 独立复现器（脱离 lsquic 三行定案）
```c
char *buf; size_t sz;
FILE *f = open_memstream(&buf, &sz);
fprintf(f, "hello 42\n");
fclose(f);
/* 鸿蒙 musl: sz==0, buf 为空；glibc/musl 上游: sz==9 "hello 42\n" */
/* 若 fclose 前 fflush(f): 鸿蒙 musl 也正常 sz==9 */
```

## 影响面
- 任何"写 memstream → fclose → 读 buffer"模式的上游测试在鸿蒙上
  可能假失败（测试本身逻辑无关）
- lsquic test_hcsi_reader 实测：80/81 其余用例全绿佐证状态机正常

## 处置
- 上游测试不可改 → 平台限制豁免申报（附复现器证据链）
- 自有代码 → memstream 用后、fclose 前显式 `fflush`
