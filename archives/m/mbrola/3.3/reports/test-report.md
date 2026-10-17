# mbrola 3.3 测试报告

> **项目**: mbrola 3.3（MBROLA 双音素拼接语音合成引擎）
> **测试日期**: 2026-09-26
> **测试环境**: HarmonyOS HongMeng Kernel 1.12.0 aarch64（HAD-W32 设备，clang 15.0.4）
> **测试类型**: 消费者语义测试（真实驱动 CLI + 已发布 mbrola-gr2 语音数据）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游自动化测试（发布包内） | 0 | —（无测试套件，说明见下） |
| 消费者测试断言 | 66 | 100% |
| 通过 (PASS) | 66 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**核心功能通过率**: ✅ **100%（66/66 断言）**

> 上游测试说明：mbrola 3.3 发布包不含 tests/ 目录、无 ctest/pytest 注册；
> Makefile `check/checkold` 依赖私有 `UTILITY_TCTS` 双音素语料（发布包中不存在，
> `find . -name 'UTILITY_TCTS*'` 为空），因此上游测试用例数为 0，未能执行，
> 不计入通过率分母（详见 `test_package/MANIFEST.yml` 与 `notes.md`）。

---

## 二、测试结论

### 2.1 总体评价

✅ **mbrola 3.3 在 OHOS/aarch64 上编译、打包与核心合成功能全部通过验证。**

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游 CLI 无 `--version/--help` 长选项（仅 `-h`） | CI L2 冒烟为非阻塞告警 | 🟢 |
| 上游无自动化测试 | 需自行补全消费者测试（本报告） | 🟢 |

### 2.3 可用功能清单

```
✅ 命令行合成：mbrola <database> <pho_file+> <output_file>
✅ 输出格式：WAV / AU / RAW / AIFF（按扩展名）
✅ 时长/频率/音量/声线比例：-t / -f / -v / -l
✅ 数据库信息与音素表：-i
✅ ROM 数据库转储与加载：-W / -w（与直渲染字节级一致）
✅ 未知音素错误恢复：-e / IGNORE
✅ 管道输入输出与 FLUSH/COMMENT/重命名/克隆选项
```

### 2.4 已知限制

1. 上游无自动化测试套件，`make check` 依赖未随包分发的 `UTILITY_TCTS` 语料。
2. `--version/--help` 不被支持（上游 CLI 仅短选项）；CI L2 对此为非阻塞告警。
3. 语音合成需要外部语音数据库（如本仓库已适配的 `mbrola-gr2`）。

---

## 三、测试详情

### 3.1 通过的测试（`test_package/test_mbrola_consumer.py`，8 场景 66 断言）

| 测试项 | 功能 | 断言数 | 结果 |
|--------|------|--------|------|
| fixtures | 二进制/数据库/乐谱存在；乐谱 211 条指令、总时长 17264ms | 5 | ✅ PASS |
| cli_contract | 裸执行 banner、`-h` 用法；非法选项/缺失数据库/缺失乐谱/`-v 0` 的退出码与消息 | 16 | ✅ PASS |
| database_info | `-i` 显示 GR2 身份、release、SAMPA 音素表、静音音素行 | 5 | ✅ PASS |
| real_synthesis | 211 条音素真实合成：WAV 头/22050Hz/mono/16bit；时长 17.257s vs 乐谱 17.264s；峰值 >1000、RMS >100、双极性波形；二次渲染字节级一致 | 12 | ✅ PASS |
| runtime_options | `-t 2.0` 时长×2（±2%）；`-v 0.5` RMS×0.5（±2%）；`-f 2.0` 波形变化而时长不变；`-l 14000` 时长≈14000/22050 | 10 | ✅ PASS |
| output_formats | `.au`（`.snd` 头、data offset 28、编码 3、22050Hz、数据大小=WAV）；`.raw` 大小=WAV 数据 | 9 | ✅ PASS |
| rom_roundtrip | `-W` 生成 ROM（>6MB）；`-w` 渲染与直渲染**字节级一致** | 5 | ✅ PASS |
| error_recovery | 未知音素默认退出非 0 且报 `Unknown`；`-e` 下成功输出（0.196s） | 4 | ✅ PASS |

**合计：66/66 断言通过（100%）**

### 3.2 失败的测试

无。

### 3.3 跳过的测试

| 测试项 | 跳过原因 |
|--------|----------|
| 上游 `make check/checkold` | 依赖私有 `UTILITY_TCTS` 语料，发布包中不存在；上游无测试套件 |

---

## 四、关键问题分析

### 问题1: codeload 源码 URL 在 conan `get()` 中触发 BadZipFile

**现象**：
```
mbrola/3.3: Error in source() method
BadZipFile: File is not a zip file
```

**根因分析**：
codeload 下载 URL 以 tag 名（`3.3`）结尾、无文件扩展名，Conan `get()` 自动推断的
文件名没有 `.tar.gz` 后缀，回退到 zip 解码器。

**解决方案**：
`get(..., filename="mbrola-3.3.tar.gz")` 显式指定 tarball 名称（与仓库内 abcmidi
等 204 个 codeload 先例一致）。

### 问题2: 设备侧 `conan-verify` 的 E017 镜像注入不可达

**现象**：
```
WARN: network: Error downloading file https://ghfast.top/https://github.com/...
Read timed out
```

**根因分析**：
验证工具会为 GitHub URL 临时注入 `ghfast.top` 镜像；该镜像在当前设备网络不可达，
而设备直连 GitHub/codeload 正常。

**解决方案**：
改用 GitHub 官方 codeload 下载端点（与 `archive` 链接同一实体，SHA256
`c01ded2c…b558` 完全一致）；平台 CI 侧仍由流水线自行追加镜像回退。

---

## 五、测试环境

```
设备: HarmonyOS PC (HAD-W32/W24, aarch64), HongMeng Kernel 1.12.0
工具链: OHOS SDK 26.0.0.18 native clang 15.0.4 (aarch64-linux-ohos)
构建: conan 2.29.1 (OHOS-adapted), profile ohos-aarch64-device
mbrola: 3.3 (官方 tag 3.3, commit 6176f70), 包 ref mbrola/3.3@ohpcd/stable
测试数据: mbrola-gr2/0.0.20010521 (GR2 希腊语 22050Hz 双音素库, 211 条示例乐谱)
命令: python3 scripts/ohc-run.py conan-verify mbrola 3.3 --profile ohos-aarch64-device
      → G0–G4 PASS; test_package: 66/66 assertions passed
```

---

*报告生成时间: 2026-09-26*
