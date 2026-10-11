# bitstream 1.6 适配笔记

## 形态

VideoLAN bitstream：**header-only** 库，249 个 C 头文件（mpeg/dvb/atsc/scte/
ieee/ietf/itu/ebu 等族的位流读写 inline 函数），装到 `include/bitstream/`。
上游无 configure，纯 Makefile；`examples/` 兼作测试面。

## 做法与验证

- `package_type="header-library"`、`package_id().clear()`，只装头文件；
  `build()` 用 OHOS SDK clang 编译上游全部 7 个 example 程序（编译证据）。
- **上游测试实跑**：`examples/dvb_gen_si.test.sh` 是上游唯一测试（PSI 生成 →
  解析 → 与 golden 输出 diff）。脚本本身用 `make local` + `git diff`，只在
  git checkout 可跑；tarball 场景改为在 build() 里跑同一管线：
  1. **双跑确定性**：`dvb_gen_si | dvb_print_si`（文本与 `-x xml` 两路）各跑
     两次，输出必须字节级一致；
  2. **golden 比对（豁免 2 处上游过期格式）**：与随包 golden diff，唯一允许
     的差异是 EIT `duration_dec` 的补零格式（golden `"01:00:00"` vs 代码
     `"1:00:00"`）和 desc 0e `maximum_bitrate` 打印字段演进——golden 上次
     重生成是 **2016-11-23**（早于 1.6 的打印代码），上游自己的脚本在全新
     1.6 git checkout 上同样失败，属**上游自身缺陷**、与平台无关；其余内容
     必须逐字节一致。两项在真机均 PASS。
- 消费者测试 `test_bitstream.c`：合成 188 字节 TS 包（PID/unit start/payload
  标志）内嵌单节目 PAT，用库的 writer API 构造、reader API 读回，断言全部
  字段 round-trip；并 `#include <bitstream/dvb/si.h>` 伞头证明整个 DVB SI
  头族可编译。13 项断言全过。

## 坑

- 无 OHOS 特有坑（不影响功能）：头是 freestanding C99，零补丁。
- **bionic iconv 无 ISO6937**：`dvb_print_si` 对标记为 ISO6937 的字符串
  `iconv_open("UTF-8","ISO6937")` 失败，stderr 打印
  `couldn't initiate conversion from ISO6937 to UTF-8` 后走原始字节回退；
  输出与确定性/golden 比对不受影响（测试字符串均为 ASCII）。
- `examples/Makefile` 只在 `uname -s == Linux` 时加 `-lrt`，HarmonyOS 自动
  跳过（bionic 无 librt，`clock_*` 在 libc），正好无需处理。
- 顶层 Makefile 的 `ln -nsf .. examples/bitstream`（供 examples 以
  `<bitstream/...>` 路径包含）在配方里由 Python `os.symlink` 预建，避开
  make 在 HMDFS 上建符号链接的偶发问题。
- **上游 golden 过期**（详见上文）：2016-11 后打印代码演进未同步 golden，
  比对口径豁免 2 处格式差并留双跑确定性证明。
- 源站 `download.videolan.org` 真机可达；该域名不在 CI 镜像映射表里，CI 依赖
  预下载重试直连。
