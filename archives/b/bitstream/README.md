# bitstream — VideoLAN 位流头文件库

`bitstream` 是 VideoLAN 的 header-only 位流解析/生成库，提供 MPEG TS/PS、
DVB SI/PSI、ATSC、SCTE、IEEE/IETF/ITU 协议族的读写 inline 函数，广泛用于
`dvbtools`/`bitstream examples`（dvb_print_si、dvb_gen_si 等）。

## OHOS 适配要点

- **header-only**：249 个头文件装到 `include/bitstream/`，零编译产物、零补丁、零三方依赖。
- **上游测试实跑**：`examples/dvb_gen_si.test.sh` 的 golden 比对（文本+XML）
  在 `build()` 内按 tarball 口径复现，双比对通过。
- `examples/Makefile` 的 `-lrt` 仅在 Linux 加，HarmonyOS 自动跳过。

## 产物

| 路径 | 说明 |
|------|------|
| `include/bitstream/**` | 249 个协议位流读写头文件 |

## 参考资料

- 上游仓库：<https://code.videolan.org/videolan/bitstream>
- 许可证：MIT
