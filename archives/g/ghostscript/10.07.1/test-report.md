# ghostscript 10.07.1 上游测试报告

**日期**: 2026-08-22
**平台**: HarmonyOS PC (aarch64), HongMeng Kernel 1.12.0
**编译器**: clang 15.0.4 (aarch64-unknown-linux-ohos)
**被测二进制**: `/data/storage/el2/base/.conan-build-ghostscript-10.07.1/install/bin/gs`
**版本输出**: `gs --version` → `10.07.1` ✅

---

## 一、上游测试用例构成

| 类别 | 位置 | 说明 |
|------|------|------|
| `make check` 目标 | Makefile.in L837 | `check : default` + `$(NO_OP)` —— **空操作**，仅重新编译，无独立测试套件 |
| PostScript 运算符测试 | `lib/acctest.ps` (99 行) | 测试 PostScript 运算符的访问控制（executeonly/noaccess/readonly） |
| 渲染样本 | `examples/*.ps` `*.eps` `*.pdf` | 18 个 PostScript/EPS/PDF 样本文件，用于实际渲染验证 |
| CJK 测试 | `examples/cjk/` | 12 个 CJK 字体渲染测试脚本，**需 CID-keyed 字体支持** |
| 回归测试基础设施 | `toolbin/tests/*.py` | `gscheck_testfiles.py`/`gscheck_raster.py`/`gscheck_pdfwrite.py` 等 —— 需预生成参考校验和数据库（release tarball 未提供，无法直接运行） |

**结论**: ghostscript 上游无标准 `make check` 测试套件。可直接运行的测试为 `lib/acctest.ps`（运算符测试）和 `examples/` 样本渲染。

---

## 二、测试执行结果

### TEST 1: PostScript 运算符访问测试 (`lib/acctest.ps`)

```
$ gs -dNODISPLAY -dNOPAUSE -dBATCH lib/acctest.ps
```

| 项目 | 结果 |
|------|------|
| exit code | 0 |
| 状态 | ✅ PASS |
| 说明 | 运算符访问控制（executeonly/noaccess/readonly）全部按预期触发错误或允许访问，无异常 |

---

### TEST 2: PostScript 样本渲染 (10 个 .ps → PNG)

```
$ gs -dNOPAUSE -dBATCH -sDEVICE=png16m -r72 -sOutputFile=<out>.png <sample>.ps
```

| 样本 | 输出大小 | 结果 |
|------|---------|------|
| alphabet.ps | 25540 B | ✅ |
| colorcir.ps | 45561 B | ✅ |
| doretree.ps | 40361 B | ✅ |
| escher.ps | 63854 B | ✅ |
| grayalph.ps | 3262 B | ✅ |
| snowflak.ps | 54613 B | ✅ |
| spots.ps | 3196 B | ✅ |
| waterfal.ps | 24601 B | ✅ |
| vasarely.ps | 34287 B | ✅ |
| transparency_example.ps | 3103 B | ✅ |

**小计**: 10/10 PASS

---

### TEST 3: EPS 样本渲染 (3 个 .eps → PNG)

| 样本 | 输出大小 | 结果 |
|------|---------|------|
| golfer.eps | 16482 B | ✅ |
| ridt91.eps | 9914 B | ✅ |
| tiger.eps | 36178 B | ✅ |

**小计**: 3/3 PASS

---

### TEST 4: PDF 样本渲染 (4 个 .pdf → PNG)

| 样本 | 输出大小 | 结果 |
|------|---------|------|
| annots.pdf | 101201 B | ✅ |
| spots2.pdf | 3195 B | ✅ |
| text_graph_image_cmyk_rgb.pdf | 161451 B | ✅ |
| text_graphic_image.pdf | 162555 B | ✅ |

**小计**: 4/4 PASS

---

### TEST 5: CJK 渲染 (12 个)

| 样本 | 结果 | 说明 |
|------|------|------|
| gscjk_ac.ps | ✅ | 15498 B |
| gscjk_ag.ps | ✅ | 15059 B |
| gscjk_aj.ps | ✅ | 13125 B |
| gscjk_ak.ps | ✅ | 14392 B |
| iso2022.ps | ✅ | 31059 B |
| iso2022v.ps | ✅ | 28858 B |
| all_ac1.ps | ❌ FAIL | 缺 CID 字体 MKai-Medium |
| all_ag1.ps | ❌ FAIL | 同上 |
| all_aj1.ps | ❌ FAIL | 同上 |
| all_aj2.ps | ❌ FAIL | 同上 |
| all_ak1.ps | ❌ FAIL | 同上 |
| article9.ps | ❌ FAIL | 同上 |

**失败根因**: `Error: /undefinedresource in findresource` —— 缺少 CID-keyed 字体（MKai-Medium 等）。脚本头部已明确警告：
> "If you have not done CID-keyed fonts installation and definitions at /Resource/CMap and CIDFnmap or /Resource/CIDFont of ghostscript, then this script can't work correctly."

**判定**: 非适配缺陷。CID 字体是可选资源，ghostscript 源码不包含这些字体（需用户自行安装如文鼎字体）。6/12 PASS，6 个因缺可选 CID 字体资源失败。

---

### TEST 6: PS/EPS → PDF 转换 (ps2pdf)

| 输入 | 输出大小 | 结果 |
|------|---------|------|
| alphabet.ps | 14712 B | ✅ |
| colorcir.ps | 44354 B | ✅ |
| tiger.eps | 34710 B | ✅ |

**小计**: 3/3 PASS

---

### TEST 7: PDF → PS 转换 (pdf2ps)

| 输入 | 输出大小 | 结果 |
|------|---------|------|
| annots.pdf | 1154557 B | ✅ |
| text_graphic_image.pdf | 563732 B | ✅ |

**小计**: 2/2 PASS

---

## 三、汇总

| 测试类别 | 总数 | PASS | FAIL | 通过率 |
|---------|------|------|------|--------|
| 运算符测试 (acctest.ps) | 1 | 1 | 0 | 100% |
| PS 渲染 | 10 | 10 | 0 | 100% |
| EPS 渲染 | 3 | 3 | 0 | 100% |
| PDF 渲染 | 4 | 4 | 0 | 100% |
| CJK 渲染 | 12 | 6 | 6 | 50%* |
| PS→PDF 转换 | 3 | 3 | 0 | 100% |
| PDF→PS 转换 | 2 | 2 | 0 | 100% |
| **合计** | **35** | **29** | **6** | **82.9%** |

\* CJK 6 个失败均为缺少可选 CID-keyed 字体资源，非 ghostscript 适配缺陷。

## 四、未运行项说明

| 项目 | 原因 |
|------|------|
| `make check` | 上游目标为空操作（`NO_OP`），无实际测试 |
| `toolbin/tests/*.py` 回归测试 | 需预生成参考校验和数据库，release tarball 未提供，仅用于上游 CI |
| 内嵌第三方库测试 (zlib/test, jpeg, libpng/pngtest 等) | 随 ghostscript 一起编译，非独立测试入口 |

## 五、结论

ghostscript 10.07.1 在 HarmonyOS PC (aarch64) 平台核心功能验证通过：
- PostScript 解释器（运算符访问控制）正常
- PS/EPS/PDF 渲染到 PNG 全部成功
- PS↔PDF 格式转换全部成功
- CJK 基础渲染（gscjk/iso2022 系列）正常

唯一失败项为缺少可选 CID-keyed 字体资源导致的高级 CJK 测试，与平台适配无关，属上游已声明的可选依赖。

**测试结论: PASS**（核心功能完整，6 个 CJK 失败为可选资源缺失，非适配问题）
