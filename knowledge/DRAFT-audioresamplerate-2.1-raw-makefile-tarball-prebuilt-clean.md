# audioresamplerate 2.1：Makefile 仓库 tarball 自带预编译产物必须 clean 重建

> 草稿（DRAFT）— 来自 audioresamplerate 2.1 HarmonyOS PC (aarch64) 第一轮适配的真实日志。
> 与 `.kv` 同 stem 配对，字段见 knowledge/DRAFT-audioresamplerate-2.1-raw-makefile-tarball-prebuilt-clean.kv

## 问题

audioresamplerate 2.1 是纯 Makefile 项目（顶层 Makefile，`make iniparser/log/resamplerate/all`），
官方 release tarball（`https://codeload.github.com/AnSwErYWJ/AudioResamplerate/tar.gz/refs/tags/v2.1`，
SHA-256 `6800057700c52d6b696694f714ef4a0f11f3b28c84508edb9f70efd662fb808a`）自带
**x86-64 预编译的 `lib/libiniparser.so` / `lib/liblog.so` / `lib/libresamplerate.so`**。

OHOS arm64 交叉构建时：

- `make all`（链接 bin/resamplerate）命中 tarball 自带的 x86-64 .so，报 **incompatible**；
- 若直接打包，包内会混入错误架构二进制，消费者加载失败。

## 根因

上游仓库把构建产物提交进源码树并随 release tarball 分发；交叉编译时链接器按默认搜索路径
命中这些错误架构产物。配方不主动清理，则基于错误架构产物链接或产出污染包。

## 修复

配方 `build()` 第一动作显式清理并全量重建（`conanfile.py`）：

```python
def build(self):
    apply_conandata_patches(self)
    # 清除 tarball 自带的 x86-64 预编译 .so，必须从源码重建目标架构
    self.run("make clean cleanso", cwd=self.source_folder)
    mkdir(self, self.source_folder + "/bin")      # 上游 Makefile 不自动建 bin/
    for target in ("iniparser", "log", "resamplerate"):
        self.run(f"make {target} CC=clang", cwd=self.source_folder)
    self.run("make all CC=clang", cwd=self.source_folder)
```

要点：

1. **先 clean 再重建**：`make clean cleanso` 删除 tarball 自带预编译 .so；
2. **R33**：raw makefile 硬编码 `CC := gcc`，配方显式传 `CC=clang`（来自 OHOS profile
   工具链），不裸用 shell 环境变量；
3. **cwd=self.source_folder**（E392 第三陷阱）：raw makefile 的 Makefile 在 source_folder，
   conan 默认在 build_folder 执行会报 "No makefile found"；
4. **产物架构核验**：`readelf -h` / `readelf -d` 确认 `ELFCLASS64 / Machine: AArch64`，
   防止污染包混入错误架构二进制。

## 验证

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# build() 三库 + all 全目标成功；test_package ctest 1/1 PASS
# 产物 readelf：ELF 64-bit LSB, ARM aarch64；三个 lib/*.so + bin/resamplerate 均 aarch64
# 消费者用例（consumer_audioresamplerate.c）src_new/src_process 16k->48k PASS
```

## 适用边界

- **适用**：上游仓库把 .so/.a 等构建产物提交进源码树并随 tarball 分发（release tarball
  含 lib/ 下预编译产物）；交叉编译目标架构与产物架构不同（OHOS aarch64 vs 上游 x86-64）。
- **反例 / 不适用**：仓库纯源码（tarball 无预编译产物）时 clean 步骤无必要；产物架构与
  目标一致时无需清理。判断方式：解包后检查 `lib/` 下是否存在 .so/.a，并用 `readelf -h`
  核验其架构。

## 与既有知识的差异

- **E392**（raw-makefile-conan-recipe-pattern）覆盖 get() filename / compiler_executables /
  make cwd 三陷阱；本草稿新增"**tarball 自带预编译产物 → build() 先 clean 重建**"与
  "**产物架构 readelf 核验**"两段，互不重叠。
- **E276**（codeload BadZipFile filename=）为源码下载层；本草稿为构建层清理。
- **E475 / E522** 为 patch/cache 陈旧，与"源码树携带构建产物"不同。