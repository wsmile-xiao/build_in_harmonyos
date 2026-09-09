# Test Report — precomp 0.4.7 (OHOS PC aarch64)

Status: PASS
Date: 2026-09-04
Executor: openharmony-compile-agent (fork PR workflow)

## 1. 构建验证 (conan create)

命令：

```bash
conan create archives/p/precomp/0.4.7 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

结果：`Package '6b129b068851896169fae42d399fa922d239ce8a' created`
（Packaged 1 file: precomp；日志 reports/conan-create.log）

上游无自动化测试套件（无 check/test 目标、无 CTest；仅 appveyor.yml
Windows 构建冒烟），故无 make check 阶段，测试全部由 test_package 承担。

## 2. test_package（R34 实质测试）

驱动：test_package/test_precomp.py（python3，通过 conanfile test() 以
绝对路径调用包内 bin/precomp；所有输出写 tempfile.mkdtemp()，finally
rmtree；subprocess 均带 180s 超时）

conan create 内置执行结果（conan-create.log 原文）：

```
  [OK] --version rc=0 with version banner
  [OK] --help rc=0 with usage text
  [OK] precompress rc=0, .pcf created, 1/1 stream recompressed
  [OK] restore round-trip byte-identical (sha256 match)
  [OK] gzip(.pcf) < gzip(original): 16184 < 23129
HMBS_TEST_PACKAGE_RESULT: total=5 passed=5 failed=0
```

断言明细：
1. `precomp --version` → rc=0 且输出含 "Precomp v0.4.7"（GNU 风格长选项，
   补丁新增）
2. `precomp --help` → rc=0 且输出含 "Usage: precomp"（补丁新增）
3. `precomp -o<pcf> <弱压缩.gz>` → rc=0、.pcf 生成、输出
   "Recompressed streams: 1/1"（输入：20000 词随机文本 gzip level 1，
   ~115KiB）
4. `precomp -r -o<out> <pcf>` → rc=0 且还原文件与原文件 sha256 字节一致
   （位对位无损 round-trip，核心正确性断言）
5. `len(gzip(pcf,9)) < len(gzip(orig,9))` → 16184 < 23129（压缩增益，
   precomp 核心价值主张实测成立）

## 3. Staging 验证

包产物：/storage/Users/currentUser/.conan2/p/b/preco494d8a005980b/p/bin/precomp
（1,100,288 字节，aarch64 ELF）

- `precomp --version` → rc=0（横幅 "Precomp v0.4.7 Unix 64-bit"）
- `precomp --help` → rc=0（usage 输出）

## 4. conan-verify 门禁

`ohc-run.py conan-verify precomp 0.4.7` → **PASS**
（G0/G1/G2/G3/G4 + L2/L4/L5 全过；L2/L4/L5 为跳过-通过——G4 未能解析
cache 包 ID；L2 等效探测已手工执行：--version/--help 均 rc=0，见上节）
报告：reports/conan-verify-report.md

## 5. 探索阶段冒烟（work 目录构建产物）

- round-trip：`precomp -o out.pcf v.bin.gz` + `precomp -r -o rt.gz
  out.pcf` → sha256 一致（6c4b009a…）
- 压缩增益：xz(pcf)=16168 < xz(orig)=23168（~30% 提升，t3 场景）
- 无参运行 → banner + usage，rc=1（上游既有行为保持）
