# qoa 0-git20251017 — 适配工作笔记（Windows 阶段 1，2026-09-27）

任务：ohpcd 平台 qoa 0-git20251017 · 分支 `feat/qoa-0-git20251017`
（以平台实际显示为准，提交前核对绑定与截止时间）。

## W0 依赖分析

**无外部依赖**：qoa.h 为 stb 风格单头 C 库（QOA_IMPLEMENTATION 守卫），
实现只用 stdlib/string/math。R35 依赖检查为空集。

CLI 工具不打包：
- qoaconv：依赖上游不随源码分发的 dr_mp3.h/dr_flac.h（宏开关可去
  MP3/FLAC，但工具主体只剩 WAV 转换，且 Makefile 无 install 目标）；
- qoaplay：硬依赖 sokol_audio.h + alsa/pthread（Linux 分支），
  离线不可构建。
制品仓无上述第三方单头库包 → 按同作者已归档先例 qoi/0-git20251213
处理：header-library，无 commands.json。

## W0b 历史知识核验

- **同作者同形态先例 qoi/0-git20251213（upstream 已合入）**：版本
  口径、conandata 双 URL + filename、header-library 配方（package_id
  清空、cmake_file_name/target_name）、CMake 型 test_package
  （find_package + qoi::qoi）、HMBS_TEST_PACKAGE_RESULT 标记、顶层
  仅 manifest.yaml（无 README/commands.json）——本任务逐项镜像，
  差异仅在 qoa 有损（误差界断言）与 stdio 往返断言。
- 版本口径核验：`0-git<date>` = 该日期前最后提交（qoi notes 原文
  "2025-12-13 前最后提交"）。QOA 上游不打 tag；GitHub API 实测
  2025-05-09 之后至 2025-10-17 无提交 → pin
  ae07b57deb98127a5b40916cb57775823d7437d2（2025-05-09，merge PR
  #65 no-modulo）。HEAD 已到 2026-07-19，不可用（平台版本口径钉死
  20251017）。

## 源码要点（快照 ae07b57 实测）

- sha256 `0f36d866e3ba46798958165cdab327902e8062c7dcf75419933b5a88fe1e0caf`
  （codeload 官方归档，本地下载实测）。
- 文件：qoa.h / qoaconv.c / qoaplay.c / Makefile / LICENSE / README.md。
- API：qoa_encode(const short*, qoa_desc*, unsigned int* out_len)、
  qoa_decode(const unsigned char*, int size, qoa_desc*)、
  qoa_write/qoa_read（stdio，QOA_NO_STDIO 未定义时可用）；
  qoa_desc{channels, samplerate, samples, lms}；QOA_MAX_CHANNELS=8、
  QOA_FRAME_LEN=5120、文件魔数 'qoaf'（QOA_MAGIC 大端）。
- 有损格式：20 样本/64bit slice ≈ 3.2 bit/样本（约 5:1）。消费者测试
  不能断言逐样本一致 → 误差界 + 尺寸缩减 + stdio 往返三类断言。
- MIT（LICENSE，Dominic Szablewski）。
- 无 test/check 目标、无 fuzz/ 目录（该快照）→ 上游测试 0，MANIFEST.yml
  已记录原因。

## 测试计划

- 消费者（test_package/test_qoa.c，10 项断言，CMake test_package）：
  真实编译 QOA_IMPLEMENTATION 单编译单元；220Hz 正弦 9600 样本
  1ch/48kHz：① qoa_encode 缓冲 ② 'qoaf' 魔数 ③ 长度 >= 
  QOA_MIN_FILESIZE ④ encoded < raw/2 ⑤ qoa_decode 缓冲 ⑥ 通道数
  ⑦ 采样率 ⑧ 样本数 ⑨ max abs err <= 2048 ⑩ qoa_write/qoa_read
  往返（desc + 误差界）。
- Windows 预验证：本机 C 编译器实际编译并运行 test_qoa.c（结果仅作
  源码级预检，不代表真机）。

## 留给 MateBook 的验证项

1. R35 依赖检查：空集（无 conan 依赖），记录即可。
2. conan create + conan test：CMake 工具链下 find_package(qoa) 命中
   qoa::qoa（qoi 先例同款，风险低）；test_qoa 运行 HMBS_TEST_PACKAGE_RESULT: PASS。
3. 关注点：
   - OHOS clang 对 qoa.h 实现段的编译（C99；qoi 同款单头结构已验证
     过，无平台特有代码；若 math 链接问题加 -lm）。
   - test_qoa.c 写临时文件 test_qoa_roundtrip.qoa 到 CWD（构建目录，
     umask/HMHDFS 可写；失败时改用 TMPDIR）。
   - 误差界断言 2048 在 OHOS/ARM64 下的数值表现（x86 预检参考；
     QOA 定点实现跨平台位精确，理论无差异；若超界取实测 max_err
     修正常数并保持"误差界"语义）。
4. `ohc-run.py finish qoa 0-git20251017 built` → W4 审计（不跑 submit）。
---

**编译结束**: 2026-09-27 14:40
**最终状态**: built
