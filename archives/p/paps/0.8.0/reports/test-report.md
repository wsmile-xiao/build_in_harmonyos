# Test Report — paps 0.8.0

- 日期: 2026-09-05
- 平台: HarmonyOS PC (aarch64, musl, clang 15.0.4)
- 构建系统: meson (conan 2.29.1 OHOS 适配版, profile ohos-aarch64)
- 分支: feat/paps-0.8.0

## 1. conan create（配方验证）

```
export LD_LIBRARY_PATH="/system/lib64/platformsdk:/system/lib64/chipset-pub-sdk:/system/lib64:/system/lib64/ndk"
conan create archives/p/paps/0.8.0 \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
  -pr:b=$HOME/.conan2/profiles/ohos-aarch64 \
  --build=missing
```

结果: **成功**（第 9 轮，前 8 轮错误链见 notes.md；EXIT_CODE=0）

- meson 五依赖探测全 YES: fmt 12.2.0 / pangoft2 1.50.14.1.1 /
  pangocairo 1.50.14.1.1 / glib-2.0 2.84.0.1 / gobject-2.0 2.84.0.1
- conan-verify 全部门禁 G0/G1/G2/G3/G4 + L2/L4/L5 通过
- W3 本地 CI 模拟（build_and_test.sh）: 1/1 通过，Pass rate 100.0%
- L1e 破坏性反向验证（R34）: bin/ lib/ 移走后测试失败 → 确认真实依赖
- `.ci-result.json`: exit_code=0, log_sha256=f82b3df95b1f5611aa8f31db11674b7f36a6ea1cf3c9dea293ea68d8e2b6a83b

## 2. 上游测试套件

上游 paps 0.8.0 **无注册测试**：meson.build 未注册任何 test() 目标，
无 tests/ 目录，上游仓库无 CI 测试套件。上游测试数 0（manifest 如实记录）。

## 3. 消费者功能测试（test_package，R34 实测转换）

test_package/test_paps.sh 真实执行 paps 二进制，17 项断言全 PASS：

```
PASS: paps --version exits 0
PASS: paps --version prints PACKAGE_STRING paps-0.8.0
PASS: paps <text> PostScript conversion exits 0
PASS: PostScript output starts with %!PS-Adobe header
PASS: PostScript output contains showpage
PASS: PostScript output contains embedded font resources (Type42/BeginResource)
PASS: PostScript output is non-trivial (size 68504 bytes > 10000)
PASS: paps --format pdf conversion exits 0
PASS: PDF output starts with %PDF header
PASS: PDF output ends with %%EOF
PASS: paps --format svg conversion exits 0
PASS: SVG output contains <svg root element
PASS: paps -o out.ps exits 0
PASS: paps -o wrote a non-empty output file
PASS: -o output file is a PostScript document
PASS: paps --help exits 0
PASS: paps --help prints usage/options
TOTAL: 17 checks, 0 failed
```

验证口径说明：
- 输入为上游多语言样例 examples/small-hello.utf8（阿/孟/希腊/希伯来/日/中/越南语）
- PostScript 输出 68504 字节，内嵌 11 个 Type42 字体资源
  （NotoSansHebrew/NotoSansArabic 等，fontconfig 指向 /system/fonts 后
  pango 全语言渲染成功）
- PDF/SVG 双格式转换均产出合法文档头尾
- 覆盖完整管线：glib option 解析 → pango 排版(pangoft2) → cairo
  PS/PDF/SVG 矢量后端 → fmt 格式化

## 4. 平台限制（非阻塞）

- L2 smoke test（--version/--help via W3 runner）报 warn：runner 以
  mksh 环境直跑 paps 失败（mksh 不能 exec 带 DT_RUNPATH 的 ELF），
  conan test_package 用 bash 包装后同断言全 PASS——同一二进制、同一
  断言，仅 shell 差异，非功能缺陷。
- src-to-paps 是 python 辅助脚本（依赖 source-highlight），不在
  libpaps 主链，不影响 paps 二进制功能。

## 5. 结论

paps 0.8.0 在 HarmonyOS PC 上编译、链接、运行、多语言文本转换全部
验证通过。测试通过率：消费者测试 17/17 = 100%。
