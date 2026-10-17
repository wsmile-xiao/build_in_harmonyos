# draft-tanidvr-1.4.1-dhav-frame-format-ext-header-slots

## 症状

给 `dhav2mkv` 喂一份自造的 `.dhav` 录像流做端到端测试时，出现两类迷惑现象：

1. **「转换成功」但分辨率是废值**：程序 rc=0，日志只说 `Media container: DHAV`，
   产物 MKV 也有 EBML 头、有 cluster、有 H.264 负载，但反查 MKV 头的宽高是 `480x0`。
2. **同一个二进制在两种架构上行为相反**：x86_64 本机构建跑同一份流时第 4 项断言就
   `Floating point exception (core dumped)`（gdb 回溯落在 `src/mctools.c:651` 的
   `(mc_parms->v_width * 1000) / mc_parms->v_height`），而 OHOS aarch64 产物同样的流
   完全不崩。

## 根因

两个问题同源，都是「扩展头槽位错位一字节」+「架构相关的整数除零 UB」。

### 1. DHAV 帧格式（只存在于 src/mctools.c，无文档无样例）

```
偏移  0 : "DHAV"              （4 字节 magic）
偏移  4 : 帧类型              （0xfd = 带几何信息的 I 帧；0xfc = 普通视频帧，必须在 I 帧之后）
偏移 12 : 帧总长度 (u32 LE)   （与尾部冗余重复，两处必须一致）
偏移 16 : epoch     (u32 LE)
偏移 20 : 相对时间戳 ms (u16 LE)
偏移 22 : 扩展头长度
偏移 24 : 扩展头（长度 = 偏移 22）
其后    : body（H.264 Annex-B）
尾部 8B : "dhav" + 帧总长度 (u32 LE)
```

`dstf_process_dhav_stream_to_frames()` 会校验偏移 12 的长度、尾部 `dhav` 位置
（`总长-8`）和尾部 u32 三者一致，不一致就逐字节丢弃当垃圾。

### 2. 扩展头是「稀疏数组按组填充」，不是 TLV

`dhav_sf_parse_ext_head()` 每 4 字节读一个 id（**只有 id==0x88 是 8 字节**），然后把这 4 个
字节依次写进 `dhav_subfields_array[id<<3 + 子位]`：

| 写入 | 值 |
|---|---|
| 子位 0 | id 自身 |
| 子位 1 | 组内第 1 字节 |
| 子位 2 | 组内第 2 字节 |
| 子位 3 | 组内第 3 字节 |

读取端（`dt_collect_dhav_frame_info()`）：

```c
v_width  = DHAV_SF_DATA(0x80, 0x02) * 8;   /* 组内第 2 字节 */
v_height = DHAV_SF_DATA(0x80, 0x03) * 8;   /* 组内第 3 字节 */
dhav_fps = DHAV_SF_DATA(0x81, 0x03);       /* 0x81 组组内第 3 字节 */
```

所以 **640x480@25fps** 的扩展头是 `80 00 50 3C 81 00 00 19`，而很容易写成
`80 50 3C 00 81 00 00 19` —— 后者让 height 落到 0、width 变成 480（实测产物 MKV 头
`PixelWidth=480 PixelHeight=0`）。

### 3. 架构相关的整数除零 UB

`mctools.c:651` 用 `(v_width * 1000) / v_height` 猜宽高比，`v_height` 是 `uint32_t`
且上游未做零值防御：

- **x86_64**：`idiv` 除零 → SIGFPE 崩溃；
- **aarch64**：`UDIV`/`SDIV` 除零按架构定义**返回 0、不陷阱**，实测 rc=0 正常产出
  1009 字节 MKV（头 480x0）；
- **clang -O3**：除数为编译期常量 0 时直接折叠成任意值（实测同一段代码在 x86 上
  quotient=1），属于 UB，任何结果都不该依赖。

## 解决方案

1. 扩展头按「每组 4 字节 = `[id, -, width/8, height/8]`」写：`80 00 50 3C 81 00 00 19`。
2. **用产物反查解析结果**，别只看「转换成功」：`mctools.c` 把宽高以大端 uint16 写在 MKV 头
   固定偏移 `MKV_HOFF_PixelWidth = 0x16e + 2 = 0x170`、`MKV_HOFF_PixelHeight = 0x174`，
   测试里加两条断言 `struct.unpack_from(">H", mkv, 0x170) == 640` /
   `== 480`，构造数据错位立刻会被抓到。
3. 跨架构结论不要互相迁移：设备/target 架构上「没崩」不代表数据合法；审计或复审在 x86 上
   跑出的 SIGFPE 也不代表 aarch64 上会崩 —— 两边都要看。

## 验证

- tanidvr/1.4.1 `conan create`（OHOS aarch64）test 阶段 25/25 断言全绿，含上述两条宽高断言。
- 复审在 x86_64 上复现 SIGFPE，确认根因是扩展头槽位而非配方问题；按本条修正后两侧一致。
- `dhav2mkv` 另有上游行为瑕疵：输入文件打不开时 `process_dhav_stream()` 返回 4，但 `main()`
  忽略返回值直接 `exit(0)`；无法识别的容器也会 fallback 当 DHAV 继续跑（0 字节输出、
  退出码 0）—— 断言要落在日志文本与输出内容上。
