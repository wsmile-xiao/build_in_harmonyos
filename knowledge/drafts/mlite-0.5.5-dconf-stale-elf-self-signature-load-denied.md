# 制品仓依赖的预编译 .so 可能带“失效的自签名”：OHOS 加载器一律 Permission denied，且编译/链接期完全无感（只在运行期暴露）

> Draft: `DRAFT-MLITE-055-DCONF-STALE-ELF-SELF-SIGNATURE-LOAD-DENIED`
> Stem: `mlite-0.5.5-dconf-stale-elf-self-signature-load-denied` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-MLITE-055-DCONF-STALE-ELF-SELF-SIGNATURE-LOAD-DENIED
- **严重度**: 3（3=🔴blocking / 2=🟡medium / 1=🟢minor）
- **类别**: runtime|elf-signature|dependency-defect|ohos-platform
- **触发工具**: runtime
- **阶段**: runtime

## 错误特征

```
Error loading shared library libdconf\.so\.1.*Permission denied|Error relocating .*dconf_client_new: symbol not found
```

匹配关键词：`dconf, libdconf.so.1, Permission denied, Error loading shared library, .codesign, self-sign, binary-sign-tool, dlopen, NEEDED`

## 根因

OHOS 对可执行映射做 ELF 代码签名校验：文件内 .codesign 段必须与文件内容一致。dconf/0.40.0 的 libdconf.so.1.0.0 自签名与内容不匹配（全新 CONAN_HOME 从制品仓重新下载，md5 7b5bc901dbda4cb2333959ff68f376be 仍一致且仍失败；同批次下载的 expat 同平台可正常加载，排除下载/HMDFS 破坏）。任何链接 libdconf.so.1 的可执行体都会在加载阶段失败：`Error loading shared library libdconf.so.1: (needed by …)` + `Permission denied`；即便用 llvm-objcopy 改动任意已签名库（如 libQt5DBus.so）也会立刻变成同样的 Permission denied → 说明校验确实存在。

## 影响范围

所有依赖该二进制的包（包括只做 conan download/install 判“可消费”的验收流程——编译链接全绿，运行期才炸）；test_package/L2 smoke test 会因此失败。

## 验证命令

```bash
python3 -c "import ctypes;ctypes.CDLL('<pkg>/lib/libdconf.so.1')"   # OSError: … Permission denied
```

## 处置建议

- **优先级**: 1
- **方案**: `re-sign-or-republish-dependency-and-gate-on-runtime-load`
- **说明**: (1) 判定口径升级：依赖"可消费"不能只看 conan download / 链接成功，必须做一次 dlopen 或运行期冒烟（本次即由 test 阶段暴露）；(2) 临时验证/绕行：用 SDK 的 binary-sign-tool 重新自签名到本地目录再置于 LD_LIBRARY_PATH 前部：`binary-sign-tool sign -selfSign 1 -inFile <坏库> -outFile <新库> -signAlg SHA256withECDSA`，实测重签后可正常加载；(3) 正解：重出该依赖包（版本递增 X.Y.Z.N）并重新上传（重签名/重建即可，配方无需改动）；(4) 注意 OHOS 上禁止事后改 ELF（objcopy/patchelf 会破坏签名），因此 rpath 等只能在链接期决定。
- **参考命令**: `/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/toolchains/lib/binary-sign-tool sign -selfSign 1 -inFile libdconf.so.1.0.0 -outFile libdconf.so.1 -signAlg SHA256withECDSA`
- **可自动修复**: false

## 可复用知识总结（同类问题通用）

- **问题类**：制品仓**预编译二进制的 ELF 自签名与内容不符** → OHOS 加载器一律 `Permission denied`；编译/链接期完全无感，只在**运行期**暴露。
- **识别信号**：`Error loading shared library <lib>.so: (needed by …)` / `… Permission denied`；`python3 -c "import ctypes;ctypes.CDLL('<lib>')"` 同样失败；`readelf -SW` 存在 `.codesign`；`display-sign` 显示 `self-sign`。
- **判别方法（三步排除法）**：① 全新 `CONAN_HOME` 从制品仓重下，比对 md5 是否与缓存一致（排除本地损坏）；② 同批次下载的**其它库**能否 `dlopen`（排除下载/HMDFS 破坏）；③ 用 SDK `binary-sign-tool sign -selfSign 1 -inFile <坏库> -outFile <新库> -signAlg SHA256withECDSA` 重签后能否加载——能加载即坐实"签名失效"。反证法：对**已知可用**的库做 `llvm-objcopy` 任意改动，若立刻同样 `Permission denied`，说明加载器确实在校验签名。
- **通用处置**：本地验证可重签到独立目录并置于 `LD_LIBRARY_PATH` 首位；**正解是重出依赖包并重新上传**（配方通常无需改动，重编译即可重签名）。注意 **OHOS 上禁止事后改 ELF**（改 rpath/objcopy 都会破坏签名）。
- **适用范围**：所有依赖"制品仓预编译 .so"的适配任务；**把"可消费"判定从 download/链接成功升级为 dlopen/运行期冒烟**。
