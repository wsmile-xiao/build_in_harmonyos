# pcapfix 1.1.7 — 无 --version 工具的 L2 门禁与确定性功能测试（draft）

**Category**: ci | testing | ohos · **Severity**: 2 · **Tool**: conan/build_and_test.sh

## 症状

- CI L2 阶段输出 `[warn] L2: pcapfix --version/--help failed (non-blocking)`。
- pcapfix 1.1.7 的 getopt 串 `":t:ko:v::d::s::n::"` 里 `-v` 是 verbose，没有
  版本/帮助选项；无参数时打印 usage 且 `return(-1)`。

## 根因

1. `ci/conan/build_and_test.sh` 的 L2 依次试 `--version`、`--help`，双失败仅
   **非阻塞 warn**（源码核实 "non-blocking"）。
2. 此类包不能靠 L2 出冒烟证据；给上游加假 `--version` 补丁纯属为过门禁改
   产品行为，不可取。

## 对策

test_package 自带确定性功能断言，把"没有版本选项"本身变成被测契约：

1. 无参数调用 → 断言非零退出 + stdout 有 `Usage`。
2. 内联 printf 夹具：最小合法 pcap（LE magic `d4 c3 b2 a1`、v2.4、snaplen 65535、
   linktype 1、2×76B 包），只清零 4 字节 magic。源码级确定：`hdr_integ=1 < 4` →
   CORRECTED 分支 → `res=1` → `[+] SUCCESS: 1 Corruption(s) fixed!` + `return 0`。
3. 断言退出码 0、SUCCESS 横幅、输出文件 magic 恢复（双端序兼容）、大小不变。

## 夹具时间戳坑（真机实测）

多包夹具的 ts_sec 必须**小端字节序**且相邻包差 ≤ 86400 秒（`is_plausible` 硬模式
`-10/-12` 检查）。首版把 ts_sec 写成大端字节（`00 00 00 01` = LE 16777216），相邻包
ts 暴涨千万秒 → pcapfix 判定不合理 → ASCII 损坏暴力重同步，把完好的 4 包文件"修"成
2 包 + `SUCCESS: 3`。多包统一用同一现实时间戳（`\x5f\xe2\x24\x5f`）最稳。

## 验证

LAN 真机 conan create：`pcapfix smoke test OK`（9/9 检查点）。
