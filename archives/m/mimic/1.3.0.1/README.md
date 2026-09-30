# mimic 1.3.0.1 (HarmonyOS PC / ohos-aarch64)

Mycroft 的轻量级 TTS 语音合成引擎（CMU Flite 分支 + 内嵌 HTS 引擎），
适配 HarmonyOS PC（arm64），以 Conan 包形式发布。

- 上游：<https://github.com/MycroftAI/mimic1>
- 适配笔记：[notes.md](./notes.md)
- 构建清单：[manifest.yaml](./manifest.yaml)

## 使用

```sh
conan install --requires=mimic/1.3.0.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

静态库形态（`--enable-static --disable-shared`），链接 `-lttsmimic ...`；
HTS voice 数据在 `share/mimic/voices/cmu_us_slt_hts.htsvoice`。

示例（HTS voice）：

```c
#include "mimic.h"

cst_voice *register_cmu_us_slt_hts(const char *voxdir);

/* HTS 引擎按 CWD 解析 voices/cmu_us_slt_hts.htsvoice：
   先 chdir 到 <pkg>/share/mimic/voices 再注册 */
mimic_init();
cst_voice *v = register_cmu_us_slt_hts(".");
cst_wave *w = mimic_text_to_wave("hello", v);
```

注意：`mimic_voice_load()` 仅支持 CG (.flitevox) 语音；HTS 语音需用
`register_cmu_us_slt_hts()`（同上游 `mimic -voice slt_hts` 的路径）。
