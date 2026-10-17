# lfanew — MS-DOS MZ 存根工具

## 简介
`lfanew`（作者 TK Chia）处理 MS-DOS / Windows 可执行文件开头的 MZ 结构：
为旧式 MZ 存根补上 `.e_lfanew` 字段，把 PE 等载荷与 MZ 存根拼接（stubify），
或从“胖”可执行文件中剥离存根取回载荷（unstubify）。
同时附带一个小型 C 可移植库 `libfanew.a` 与头文件
`<lfanew/dirent.h>`（scandir / `_direntdup`）、`<lfanew/io.h>`（`_binmode`）、
`<nexgen/mzendian.h>`（非对齐小端存取）、`<nexgen/mzhdr.h>`（`mz_hdr_t`）。

## 版本历史
- 0-20230825: 编译成功 (2026-09-26)，上游 tag `20230825`

## 特点
- 纯 C，autotools（上游自带 configure），无第三方依赖
- 自带 2016 年 config.sub，不认 ohos 三元组，配方以 `--host=aarch64-unknown-linux-musl` 配置
- `lfanew` 只依赖 libc，静态链接交付

## 用法
```bash
lfanew -o new.exe old.exe                 # 为旧式 MZ 存根添加 .e_lfanew
lfanew -S -o fat.exe payload.exe stub.exe # 把载荷挂到 MZ 存根后面
lfanew -U -o payload.exe fat.exe          # 剥离存根，取回载荷
```
