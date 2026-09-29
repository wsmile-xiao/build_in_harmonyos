# DRAFT-E739-ohos-snd-eacces-device-test-skip

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-E739-ohos-snd-eacces-device-test-skip.kv`

**标题**：OHOS 上 /dev/snd 存在但全部 EACCES：ALSA 设备依赖用例的探针 + filter + SKIP 计数口径（不写 PASS）

**阶段: `testing` · 触发: `conan|ctest|gtest` · 类别: `testing, portability, ohos, device, conan-recipe` · 严重级: `2`**

## 错误签名（error_signature）

```text
|-
  cannot open card\([0-9]+\) device \([0-9]+\): Permission denied|
  /dev/snd: errno=13\(EACCES\) Permission denied|
  /dev/snd/controlC[0-9]+: errno=13\(EACCES\) Permission denied|
  pcm_is_ready\(pcm_object\).*Actual: false|
  mixer_open.*Expected: .mixer_object. != .nullptr.
```

## 根因（root_cause）

|-
  HarmonyOS PC 内核有 sound 子系统，`/dev/snd` 目录确实存在，但普通进程对目录与
  `controlC0/C1/C2` 节点一律 `EACCES`（能力位不含 DAC override，也没有音频组权限）。
  tinyalsa 2.0.0 的 68 条 gtest 注册用例里有 66 条必须在 SetUp 或用例体里打开
  control/pcm 节点：全量跑的结果是 `66 FAILED`，失败断言只有两类——
  `pcm_is_ready(...) Actual: false` 与 `mixer_object != nullptr` 实际为 NULL，另有
  `cannot open card(N) device (N): Permission denied` 的原始错误行。
  这类失败与被测代码正确性无关，但直接把它们写成 FAIL 会把适配判成大面积红，
  写成 PASS 是红线；正解是**先取证再分类**：
  1. 配方 build() 里用 os.open 对 `/dev/snd` 与 controlC* 做探针，把 errno/错误码
     逐字打进日志（一手证据，不是推测）；
  2. 探针失败 ⇒ 用 `--gtest_filter` 只跑与设备无关的子集（tinyalsa 是
     MixerTest.OpenAndClose + PcmTest.FormatToBits 共 2 条），该子集由 ctest 把关，
     失败即构建失败（不放松判据）；
  3. 用 `--gtest_list_tests`（配合同一 filter）机械清点 total/ran/skipped 并逐条打印
     SKIP 名单，四分项 TOTAL = PASS + FAIL + SKIP + NOT_RUN 恒等；
  4. 探针成功（有设备的机器）⇒ filter 自动放开为 `*` 跑全量。

## 方案（rec_approach）

probe-then-filter-then-counted-skip

## 关键词

tinyalsa, ALSA, asound, /dev/snd, EACCES, Permission denied, cannot open card, pcm_is_ready, mixer_open, 无音频设备, 设备依赖用例, gtest_filter, 探针, 环境限制, SKIP, 四分项, gtest_list_tests

## 来源

本条目取自 `knowledge/drafts/DRAFT-E739-ohos-snd-eacces-device-test-skip.kv`；promote 后对应 `knowledge/doc/E###.md`。
