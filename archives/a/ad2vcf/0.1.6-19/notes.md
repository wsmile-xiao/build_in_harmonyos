# ad2vcf 0.1.6-19

## 状态

- 状态: adapted
- 类型: command-line tool
- 源码: https://github.com/auerlab/ad2vcf
- 上游 tag: 0.1.6
- Conan 版本: 0.1.6-19

## 适配说明

- 构建单个可执行程序 `ad2vcf`。
- 依赖 `biolibc/0.2.7` 和 `libxtend/0.2.1`。
- 构建期生成 `sysexits.h` 和 `sys/param.h` 兼容头。
- OHOS 构建使用 `-fPIE` 和 `-pie`，并在 build/package 阶段对 ELF 签名。
- `VERSION` 宏固定为上游版本 `0.1.6`，避免源码包中没有 `.git` 时显示 `Unknown-version`。

## 测试说明

- build 阶段在 `can_run()` 为真时运行上游正向 fixture：`ad2vcf Test/test.vcf 10 < Test/test.sam`，并与 `Test/test-ad-correct.vcf` 对比。
- 上游 `Test/test.sh` 共 5 个测试条目：1 个正向 fixture 和 4 个负向排序检查。
- 当前上游执行口径为 1/5：已自动执行并通过 1 个正向 fixture；另外 4 个负向条目在脚本文本中明确写为“should fail with complaints about input sorting”，并在每个条目后调用交互式 `pause()`，需要人工确认失败原因和提示文本，因此未计入无人值守自动通过。
- test_package 运行 `ad2vcf --version`，并重复上游正向 fixture 对比。

## OHOS Validation

- Date: 2026-08-09, SSH port 33332, isolated job `ad2vcf-deps-upstream-20260809-r1`.
- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-ad2vcf-deps-upstream-ad2vcf-r1-20260809-060023-42957`.
- Full package reference: `ad2vcf/0.1.6-19#94c03b3961e256545d00c35c92b891d8:0b78a14a2a5be5230f73cf0d866b255d6e70c10e#f00c0c303a6a9a859133b55159ab9a1a`.
- Dependency refs: `biolibc/0.2.7#ce95827db17822d034060486f5837b9a:a4bb9bf6232620867f94106b3984a095c1c7f2f8#0b5074eb8aa832e6c77c2e6d9117f15d`, `libxtend/0.2.1#518375c9b2b56e3d5393a71846a836ff:f23d5a9b1d537641c03c7814478a2fadb727650a#30efeec57878d83467f040f1b7e7aae4`.
- Upstream Test inventory: 5 entries in `Test/test.sh`; executed 1 positive fixture, passed 1; 4 interactive negative checks not run.
- CI gates: L0 pass, L1 pass, L2 pass (`ad2vcf --version`), L4 pass, L5 pass.
