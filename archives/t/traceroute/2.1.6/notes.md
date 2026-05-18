# traceroute 2.1.6 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-14
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码：`wget http://deb.debian.org/debian/pool/main/t/traceroute/traceroute_2.1.6.orig.tar.gz`
2. 解压并初始化：`ohc-run.py init-build traceroute 2.1.6`
3. 编译：`make env=yes CC=clang prefix=$DEFAULT_PREFIX`
4. 手动链接（绕过 LIBDEPS 问题）：`clang -s -o traceroute *.o ../libsupp/libsupp.a -lm`
5. 安装到 staging：`cp traceroute $TEST_PREFIX/$DEFAULT_PREFIX/bin/`
6. 制作预编译包：`ohc-run.py package traceroute 2.1.6`
7. 本地安装：`make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Make.rules LIBDEPS 包含 `-lm` 导致 make 失败 | `LIBDEPS = $(filter-out -L%,$(LIBS))` 过滤不完整 | 修改为 `LIBDEPS = $(filter-out -L% -l%,$(LIBS))` |
| 2 | verify-build 检查 `build_system:` 字段但 manifest 使用 `build: system:` | 脚本和 manifest 格式不一致 | 添加简化字段 `build_system: makefile` |

## 源码修改

- **Make.rules**: 修改 LIBDEPS 定义，过滤 `-l%` 选项
  ```diff
  -LIBDEPS = $(filter-out -L%,$(LIBS))
  +LIBDEPS = $(filter-out -L% -l%,$(LIBS))
  ```

## 依赖版本

- 无外部依赖，仅需标准 C 库和数学库（-lm）

## 验证结果

```bash
$ traceroute --version
Modern traceroute for Linux, version 2.1.6
Copyright (c) 2016  Dmitry Butskoy,   License: GPL v2 or any later

$ traceroute localhost -m 3
traceroute to localhost (127.0.0.1), 3 hops max, 60 byte packets
 1  localhost (127.0.0.1)  0.079 ms  0.023 ms  0.018 ms
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| traceroute-2.1.6-ohos-aarch64.tar.gz | 78KB | 预编译包 |
| traceroute-2.1.6-ohos-aarch64-debug.tar.gz | 19KB | 调试符号包 |

## 注意事项

1. **权限需求**：traceroute 需要 raw socket 权限发送 UDP/ICMP 包。当前平台测试可用。
2. **UDP 模式**：默认使用 UDP 协议，功能等同于 udptraceroute。
3. **功能完整**：支持 UDP、ICMP、TCP、DCCP 等多种探测模式。
**质量门禁**: G0-G4 全部通过
---

**编译结束**: 2026-05-14 15:31
**最终状态**: built
