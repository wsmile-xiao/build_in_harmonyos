# libmpg123 1.33.7 编译笔记

## 包名与目录说明

任务卡包名为 **libmpg123**（平台 taskBranch=feat/libmpg123-1.33.7），
归档目录按任务名建在 archives/l/libmpg123/（CI L0n 门禁以归档目录名
推导期望分支名、L0m 门禁要求首字母目录与包名首字母一致——目录必须
与任务分支精确对齐且在 l/ 下）。仓内既有归档
archives/m/mpg123/1.33.5 保持不动——两线为**异名并存**关系
（kitemmodels5 与 kitemmodels、libsigcplusplus 与 libsigc++ 同款
先例），产物保持上游命名（libmpg123/libout123/libsyn123 库 +
mpg123 工具族）。conan 包名 libmpg123，pkg/cmake 目标名
libmpg123::libmpg123。

libmpg123/1.33.7 是仓内已归档 mpg123/1.33.5 的**版本跟进件**（同上
游、同适配路径直抄改版本）。1.33.7 为安全加固版本（Windows unicode 路径转换
堆溢出修复、out123 滤波器解析越界修复、realloc 乘法溢出加固等），
构建骨架与 1.33.5 无变化。

上游 1.33.7 tarball 只带 autotools（无 CMakeLists.txt）——任务卡的
cmake 口径与上游实际不符，按任务卡指示"参考 1.33.5 配方直抄改版本"
走 autotools。

## 编译日期
2026-09-25

## 构建系统
autotools（configure + make）

## 编译选项
```bash
./configure --enable-static --disable-shared --disable-modules
```

## 遇到的问题（与 1.33.5 相同，运行时补丁复用）

### 1. HMDFS umask 默认 077
configure 中 umask 077 导致创建的文件权限不足，修改为 022。

### 2. config.guess/config.sub 需添加 HarmonyOS 平台检测
与 1.33.5 同款三处 config.sub 补丁 + config.guess HarmonyOS 分支。

### 3. configure shebang /bin/sh 不存在
改为 /system/bin/sh。

### 4. HMDFS 管道操作限制
`sort | uniq` 管道操作返回 Permission denied，导致 libtool 符号导出失败。
解决方案：使用静态库模式 `--disable-shared --disable-modules`（与 1.33.5 一致）。

## 上游测试（新增于 1.33.7 适配，1.33.5 当时未跑）

`src/tests/Makemodule.am` 的 TESTS 注册 7 个测试：

| # | 测试 | 形态 |
|---|------|------|
| 1 | src/tests/decode_fixed.sh | sh 脚本驱动 decode_fixed C 程序，验证定点解码输出字节数、单次解码、mpg123-strip 剥离后二次解码 |
| 2 | src/tests/seek_whence.sh | sh 脚本驱动 seek_whence C 程序，验证 SEEK_SET/SEEK_CUR/SEEK_END 语义 |
| 3 | src/tests/seek_accuracy.sh | sh 脚本驱动 seek_accuracy C 程序，验证 seek 精度 |
| 4 | src/tests/resample_total | C 程序，重采样总输出正确性 |
| 5 | src/tests/text | C 程序，字符串处理 |
| 6 | src/tests/textprint | C 程序，文本打印 |
| 7 | src/tests/plain_id3.sh | sh 脚本驱动 plain_id3 C 程序，ID3 解析输出与 checked-in plain_id3.txt 比对 |

全部输入（sweep.mp3、plain_id3.txt）随源码分发。build() 内 `make check
SHELL=bash` 真跑（OHOS ELF 需 bash wrapper exec）。

## Verification

- `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
  exit 0 (2026-09-25, native OHOS worker)
- Upstream tests (`make check SHELL=bash` in build()):
  **PASS: 7 / FAIL: 0 / ERROR: 0** — decode_fixed.sh, seek_whence.sh,
  seek_accuracy.sh, resample_total, text, textprint, plain_id3.sh all
  passed
- Consumer test: `test_mpg123` ran on target via bash wrapper —
  "mpg123 API test passed: decoder=NEON64, first_supported=NEON64"
- Artefacts: lib/libmpg123.a, lib/libout123.a, lib/libsyn123.a,
  bin/mpg123, bin/mpg123-id3dump, bin/mpg123-strip, bin/out123,
  include/mpg123.h, include/out123.h, include/syn123.h, fmt123.h

## 产物
- libmpg123.a, libout123.a, libsyn123.a
- mpg123, mpg123-id3dump, mpg123-strip, out123
