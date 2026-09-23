# notes.md — mkp224o 1.7.0 (OHOS / OpenHarmony PC aarch64)

## 软件简介

mkp224o 是 Tor v3 隐身服务（hidden service）的 vanity onion address
生成器：通过反复生成 Ed25519 密钥对并检查公钥派生的 base32 地址前缀，
找到带指定前缀的 `.onion` 地址。纯 C（C99），多线程（pthread），
随机源来自 libsodium 的 randombytes。

- 上游: https://github.com/cathugger/mkp224o
- 版本: v1.7.0（官方 release tarball）
- License: CC0-1.0（COPYING.txt）

## 源码与校验

- URL: https://github.com/cathugger/mkp224o/releases/download/v1.7.0/mkp224o-1.7.0-src.tar.gz
- SHA256: `e38465ea893c6032ddfd7c133cbbf0de2eeaf1c428ca563fac5e85aeb609c929`
- tarball 自带 configure（Autoconf 2.72 生成），无需 autoreconf。

## 构建系统分析（重点核查项）

1. **构建系统**: Autoconf configure + GNUmakefile（非 Automake）。
   `configure` 生成 `GNUmakefile`（由 GNUmakefile.in 模板）。
2. **无 install 目标**: GNUmakefile 只有 default/all/main/util/test/clean/
   distclean/depend 目标，package() 必须手动拷贝产物到 bin/。
3. **-march=native 注入逻辑**: configure.ac 在检测编译器 flag 支持时，
   若用户未设置 CFLAGS，最终回填 `-O3 -march=native -fomit-frame-pointer`。
   Conan profile 通过 AutotoolsToolchain 显式提供 CFLAGS（含 -O2 等），
   oldcflags 非空，因此 **-march=native 从未启用**。
   这不是运行期 CPU 探测——纯粹是编译期 flag 选择。
4. **线程**: pthread（worker.c 中 pthread_create + mutex；GNUmakefile
   MAIN_LIB 硬编码 `-lpthread -lsodium`）。OHOS musl 内置 pthread 支持。
5. **随机源**: libsodium randombytes_buf（sodium_init 初始化，
   OHOS 下走 getrandom(2)）。不使用 /dev/urandom 直读或弱随机。
6. **libsodium 硬依赖**: main.c/worker.c 引用 sodium_init、randombytes_buf、
   crypto_pwhash（passphrase 模式，检测到 ARGON2ID13 时启用 -DPASSPHRASE）、
   sodium_* 工具函数。链接 -lsodium。制品仓已有 libsodium/1.0.22（裸 ref）。
   **注意**: libsodium 只提供随机源和 passphrase KDF；Ed25519 密钥数学
   用的是上游自带的 ed25519-donna（见下），未替换密码学实现。

## CPU 优化后端与 Ed25519 实现（重点核查项）

Ed25519 后端 4+1 个，configure 互斥选择：

| 后端 | 语言 | 说明 |
|------|------|------|
| ed25519-donna | 可移植 C | **默认**（--enable-donna，也是空缺省时的回退） |
| ref10 | 可移植 C | SUPERCOP ref10，opt-in |
| amd64-51-30k | x86-64 汇编 (.S) | opt-in，aarch64 不可用 |
| amd64-64-24k | x86-64 汇编 (.S) | opt-in，aarch64 不可用 |
| donna-sse2 | C + SSE2 intrinsics | opt-in，额外 -msse2，x86 only |

- **默认后端 donna 是可移植 C**，aarch64 可直接编译运行，无需任何修改。
- **上游 AC_ARG_ENABLE 陷阱**: ed25519 后端选项的 action-if-given 不检查
  enable/disable 值——传 `--disable-ref10` 会反向 *选中* ref10 并触发
  "only one ed25519 implementation can be defined" 错误。因此本配方
  **不传任何后端参数**，ed25519impl 为空时上游自动回退默认 donna。
- **无运行期 CPU dispatch**: cpucount.c 只用 sysconf(_SC_NPROCESSORS_ONLN)
  （回退 /proc/cpuinfo）统计核心数来默认线程数，无 cpuid、无特性位探测、
  无 IFUNC。构建期选择的后端即运行期唯一后端。
- 因此 aarch64 上无"伪造 CPU 特性"问题：我们用官方可移植 C 后端，
  不触碰任何密码学检查逻辑。

## 上游测试

`make test` 构建并运行 4 个测试程序（GNUmakefile TEST_TGT）：
- test_base16 — base16 编码/解码已知向量（约 7 向量 × 2 断言）
- test_base32 — base32（onion 地址字符集）编码/解码（约 9 向量 × 3 断言）
- test_base64 — base64 编码/解码（12 向量）
- test_ed25519 — Ed25519 种子扩展/公钥派生 RFC 8032 已知向量
  （2 向量 × 2 断言，WARNF 失败时报错退出非零）

均为确定性已知向量断言测试，无网络、无长运行地址搜索。
上游 CI（.github/workflows）仅做 Docker 多发行版编译，不跑测试。

本包在 conanfile.py build() 阶段执行 `make test` 构建 4 个 KAT 测试二进制，
随后配方逐一执行 4 个二进制（4/4 通过），证据保留在 conan create 日志中
（CI L1c 从 conan create 日志识别）；test_package
再从消费者视角运行最终包内二进制做功能与 OHOS 特有检查
（test_functional.sh / test_ohos.sh）。

## OHOS 适配决策

1. 官方 release tarball（带 configure），不用代理、不用 HEAD、构建期不联网。
2. libsodium/1.0.22（制品仓裸 ref，无 channel）作为依赖；不替换 Ed25519
   实现（保持 donna）。
3. .codesign 签名：按 abx/abbtr 先例用 binary-sign-tool self-sign，
   并用 llvm-readelf 校验 .codesign 段恰好 1 个。
4. 输出 bin/mkp224o 单一可执行文件；licenses/COPYING.txt。
5. 无补丁、无源码修改。

## 已知限制

- passphrase 模式（-p）依赖 libsodium 的 ARGON2ID13；OHOS libsodium
  1.0.22 支持该算法，configure 检测通过即启用 -DPASSPHRASE（不影响
  默认路径，仅增加可选功能）。
- calcest 工具程序未打包（仅开发期估算用，非用户工具）。

## 验证结果

```bash
$ mkp224o -V
mkp224o v1.7.0
```

- 上游正式测试（build() 内）: 4/4 PASS（test_base16 / test_base32 /
  test_base64 / test_ed25519，RFC 8032 Ed25519 已知向量）
- test_package 功能测试: 1/1 PASS（低难度前缀生成、目录/hostname/
  密钥文件结构、v3 地址 56 字符 base32 字符集与长度、地址与公钥
  base32 对应关系、密钥清理）
- test_package OHOS 特有测试: 1/1 PASS（ELF64 AArch64、musl 解释器、
  .codesign、无 RPATH/RUNPATH 与宿主绝对路径、2 线程真实生成、清理）

Conan verification: conan create 全流程 PASS（源码为官方 release
tarball 直链，SHA256 e38465…c929 校验通过，无代理、无构建期联网）

## L1e 反向验证（R34，2026-09-10 复核）

精确破坏法（区别于 CI 的目录级 mv）：保留包元数据
（conaninfo.txt / conanmanifest.txt / licenses / 完整 bin/ 目录结构），
仅将实际选中包（package_id db7f54fc5868482a55dc127fce31af27f3c79820，
缓存 `~/.conan2/p/b/mkp223c54e736541d7/p`）的 `bin/mkp224o` 单文件移出后
重跑 `conan test`：

- 依赖解析正常完成（graph 完整解析 libsodium/1.0.22，无 missing binary
  错误）——排除"删缓存导致依赖解析失败冒充失败"的假阴性路径；
- 失败精确发生在 test() 方法内部（FileNotFoundError），证明测试确实
  进入 test() 后依赖被测包二进制；
- 恢复二进制后 test_package 复跑全绿，包完整性无损。

CI 自带的 L1e（build_and_test.sh，sabotage bin/ → conan test 失败 →
恢复 → L2 smoke 复检）同样通过。

## 门禁复跑记录（2026-09-10）

- conan create（--build=mkp224o/* 强制重建）: PASS，4 项 KAT 逐一
  执行（RUN 行在日志 296-302 行），并独立复跑 4 个测试二进制均
  exit=0；
- conan-verify（scripts/ohc/cli.py，G0-G4 全门禁）: PASS；
- scoped CI（CI_PACKAGES=archives/m/mkp224o/1.7.0 + prdiff）:
  G0/G0e/L0（含 L0i/L0j/L0k/L0m）/KC/JC/L1（含 L1e）/L2/L4/L5
  全部 pass，Build Summary 1/1。

---

**编译结束**: 2026-09-10 10:35
**最终状态**: built
