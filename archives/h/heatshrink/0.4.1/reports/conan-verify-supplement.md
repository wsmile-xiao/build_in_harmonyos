# conan-verify 补充证据 — G4/L2/L4/L5（工具跳过项的人工复核）

`ohc-run.py conan-verify`（2026-09-04T23:33:42）整体 PASS，但因工具未能解析
package ID，G4/L2/L4/L5 显示为跳过。本文件以真实命令补齐对应证据，
包缓存: `heatshrink/0.4.1@ohpcd/stable:4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`，
包目录: `.conan2/p/b/heats41ef47c5d6c01/p`。

## G4 产物完整性 ✅

`find <pkg>/p -type f`（除 conan 元数据外全部为声明产物）:

| 产物 | 存在 |
| --- | --- |
| include/heatshrink_common.h, heatshrink_config.h, heatshrink_encoder.h, heatshrink_decoder.h | ✅（与上游 `make install` 头文件清单一致） |
| lib/libheatshrink_dynamic.a, lib/libheatshrink_static.a | ✅ |
| bin/heatshrink | ✅ |
| licenses/LICENSE | ✅ |

## L2 平台冒烟 ✅（真实运行，非仅 --version）

```sh
<pkg>/bin/heatshrink -h
# heatshrink version 0.4.1 by Scott Vokes ...（exit 0）
<pkg>/bin/heatshrink -e hs-smoke.txt hs-smoke.hsh && <pkg>/bin/heatshrink -d hs-smoke.hsh hs-smoke.out
cmp hs-smoke.txt hs-smoke.out   # 一致 → L2_ROUNDTRIP_OK
```

打包库消费者: conan create 的 test_package 阶段 9/9 用例 PASS
（dynamic 6/6 + static 3/3，见 conan-create.log L438-L455）。

## L4 静态安全扫描 ✅（llvm-readelf 15）

对打包 `bin/heatshrink`:

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| PIE | ✅ | ELF Type=DYN 且 `FLAGS_1: NOW PIE` |
| NX | ✅ | `GNU_STACK` RW（无 E 标志） |
| RELRO | ✅ Full | `GNU_RELRO` 段存在 + `FLAGS: BIND_NOW` |

静态库无安全属性要求；动态符号 9 个未解析引用均为 libc/工具链运行时符号。

## L5 产物基线 ✅（首个版本建立基线）

| 产物 | SHA-256 |
| --- | --- |
| bin/heatshrink | `e3436f505d7ec50b59f5fdb03b3eb42e6e1a2e05e947cb8618ee16dbd4b15220` |
| lib/libheatshrink_dynamic.a | `8f353f5c7785ce2b9ef20b8a932af3fdb302182fd692672df385074ea62b019a` |
| lib/libheatshrink_static.a | `ffec904f22bb209b66a43a7b68720068610ad73317e701e5a7460acdb7a94480` |

## G2 内嵌真实测试执行（conan create 日志）

1. 配方 build() 内上游测试（设备本地执行）:
   - `./test_heatshrink_static`: Total 1600，1600 pass
   - `./test_heatshrink_dynamic`: Total 12282，12282 pass
2. test_package 消费者（conan test 阶段执行）: 9/9 PASS。

合计一次 `conan create` 内真实执行 13891 个测试用例，全部通过。
