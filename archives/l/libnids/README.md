# libnids

libnids 是一个网络入侵检测(NIDS)基础库,在 libpcap 之上实现 IP 分片
重组与 TCP 流重组,通过注册回调向消费者交付重组后的双向流数据。

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 | 产物 |
|------|------|----------|--------|------|
| 1.24 | built | 2026-09-17 | 5 | ✅ |
| 1.26 | built | 2026-09-19 | 0 | ✅ |

## OHOS 适配

- 构建系统: autotools(autoconf 2.59 + 手写 Makefile.in)
- 上游无正式测试目标(make check/test、tests/ 均无);
  以 test_package 确定性 pcap fixture 做消费者验证
  (生成脚本在测试期产出 pcap 到构建目录,二进制不入库)
- `--disable-libglib`(g_thread_init 已被移除)与
  `--disable-libnet`(仅 samples 使用)后主库零额外依赖
- 1.24 补丁要点: config.guess/config.sub 增加 ohos 三元组识别;
  src/Makefile.in 共享链接补回 $(LDFLAGS);samples 的
  rindex→strrchr 替换;configure umask 077→022(HMDFS 可写)
- 1.26 零补丁路线: 显式 `--build/--host` 绕过 config.guess/config.sub
  探测,构建期改写 umask 077→022(HMDFS),`make -j1`;
  产物补 libnids.so → libnids.so.1.26 符号链接
- 详见 [1.24/notes.md](1.24/notes.md) 与 [1.26/notes.md](1.26/notes.md)

## 依赖

- libpcap/1.10.6(唯一链接依赖,static 变体经 cpp_info 传递)

## 功能验证

- 上游正式测试: 0
- 离线 fixture 消费者测试: 2 项(single-flow / multi-flow 重组断言)
- HarmonyOS 专项: 1 项(ELF64/AArch64/PIE、NEEDED、RPATH/RUNPATH 为空)

## 参考

- https://libnids.sourceforge.io/
- https://github.com/MITRECND/libnids
