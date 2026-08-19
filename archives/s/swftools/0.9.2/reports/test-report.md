# swftools 0.9.2 测试报告

- 测试日期: 2026-08-18
- 测试环境: HarmonyOS PC aarch64 shadow CI
- CI 记录: #27249
- 验证提交: `e8ac74f0dc512d4335259b9719eaf7e5ceaf602c`

## 测试摘要

| 测试集合 | 声明/新增 | 可运行 | 通过 | 失败 | 通过率 |
|---|---:|---:|---:|---:|---:|
| 上游测试目标 | 7 | 0 | 0 | 0 | 不适用 |
| Conan `test_package` | 1 | 1 | 1 | 0 | 100% |

`test_package` 共执行 21 个断言，结果为 `21/21` 通过。上游测试通过率不作 `0/0` 或 `0%` 声明，因为官方发布包没有可运行用例。

## 上游测试边界

官方 `swftools-0.9.2.tar.gz` 中可识别 7 个测试目标：

- `lib/python/Makefile.in`: `test1` 至 `test6`
- `lib/action/Makefile.in`: `test`

发布包未包含六个 `test_*.py` 脚本和 `lib/action/test.c`；action 测试还引用未声明的旧版 t1lib、JPEG、FreeType 依赖。因此记录为 `N_declared=7`、`N_runnable=0`，构建阶段不执行这些目标。

## 消费者测试

`test_package/test_swftools.py` 验证以下行为：

1. 检查 13 个命令均已打包。
2. 执行 `swfc --version` 并校验版本为 0.9.2。
3. 用 `swfc` 将最小 `smoke.sc` 编译为 SWF。
4. 校验生成文件的长度和 `FWS`/`CWS` 头。
5. 用 `swfdump` 解析 SWF，并校验 header、文件版本和帧数。

Shadow CI 输出：

```text
G0: PASS
L0/L1/L2/L4/L5: PASS
Build Summary: Total 1, Success 1, Failed 0
test_package: swftools end-to-end smoke test passed
```

## 测试结论

Conan OHOS 构建、13 个命令的打包与签名、真实的 `swfc -> SWF -> swfdump` 消费路径均通过。当前没有库内适配阻塞。

已知边界：

- 本轮关闭 JPEG、GIF、FreeType、Fontconfig、FFTW、LAME、PDFlib/Poppler、zziplib、Avifile 及 Python/Ruby 绑定等可选能力。
- 官方 0.9.2 发布包缺少上游测试输入，无法在不补造上游文件的前提下执行其 7 个声明目标。
- 本报告仅将实际执行的消费者测试计入通过率。
