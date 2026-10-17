# tpl 1.6.1 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 (OHOS 平台, aarch64-linux-ohos triplet)
- Clang 15.0.4
- Conan 2.29.1 (OHOS 适配版, os=OHOS 枚举)

## Verification

- `init-build tpl 1.6.1`（官方 v1.6.1 release tarball，SHA256 0b3750bf...）: exit 0
- 上游测试（tests/ 目录 124 个测试程序, `make all` → perl do_tests）: 124/124 通过（0 failed）
  - 适配：上游测试硬编码 `/tmp/testN.tpl` 路径，本平台 /tmp 只读（E002），
    批量改为相对路径（测试在 tests/ 目录运行）；test67.ans 期望输出同步适配。
- `conan-verify tpl 1.6.1`: exit 0
  - G0/G1/G2（conan create clean build）/G3（系统同名库隔离 R26）/G4 全部 PASS
  - L2/L4/L5: PASS（无 cache 路径跳过）
- `finish tpl 1.6.1 published`: W2 结构 + R36 依赖 + W3 本地 CI（.ci-result.json exit_code=0, log_sha256 已记录）

## 配方要点

- 构建系统: autotools + libtool；上游 v1.6.1 tarball 不含预生成 configure，
  build() 内 `autoreconf -fi` bootstrap（tool_requires automake/1.18 + libtool/2.5.4）。
- E007: config.guess 无法识别 HarmonyOS，显式传 `--build/--host=aarch64-unknown-linux-ohos`。
- E114: HMDFS 上 config.status `umask 077` 临时目录不可写，bootstrap 后去掉 umask 077。
- E074: 并行 make 在 HMDFS 上 jobserver fifo EPERM，`-j1`。
- R26: 系统同名库静态编译（--disable-shared 默认，shared 可选）。

## test_package

- test.c 实质测试：tpl_map("i") → pack → dump(TPL_FILE) → load → unpack →
  校验 roundtrip 值 42，非空壳测试（R34/PF3）。
- Test cases: 1（roundtrip 断言）
