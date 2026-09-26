# zlib 1.3.2 适配笔记（HarmonyOS PC，os=OHOS，arch=armv8）

## 编译环境
- 构建系统: makefile（zlib 自带 configure + Makefile.in）
- 编译日期: 2026-09-24
- 编译器: `/data/service/hnp/bin/clang`（clang 15.0.4，Target: aarch64-unknown-linux-ohos）
- 目标平台: HarmonyOS PC (os=OHOS, arch=armv8/aarch64)
- Conan: 2.29.1（OHOS 适配版），profile `ohos-aarch64`（`ci/conan/profiles/ohos-aarch64`）
- 状态: built（W3 conan create 本地验证通过）

## 编译步骤（模式 B 探索性编译，工作区 .scratch/zlib-subtask/）

1. **源码下载**（R39 官方源，sha256 实测校验一致）：
   `curl -fsSL https://www.zlib.net/zlib-1.3.2.tar.gz -o zlib-1.3.2.tar.gz`
   sha256 = `bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16` ✅
   （本机 https 可直接访问 zlib.net，无需像历史 notes 那样走 http 回退；网络无问题。）

2. **configure**（R33 编译器来自 Conan conf，本探索阶段用等价显式环境变量；R26 系统同名库静态）：
   ```
   CONFIG_SHELL=/data/service/hnp/bin/bash CC=clang CFLAGS="-fPIC -O2" \
     /data/service/hnp/bin/bash ./configure --static --prefix=/
   ```
   - 注意：zlib configure 不接收 `CC=clang` 作为命令行参数（`unknown option ignored`），
     CC 必须以环境变量形式传入。
   - `--static`：只构建静态库（系统同名库 R26，不发布竞争性 libz.so）。

3. **make**：`make -j1`（R9），生成 `libz.a`（-fPIC 对象）+ example/minigzip/example64/minigzip64。
   完整日志: `logs/build.log`

4. **上游官方测试**（R51）：`make check`，实际执行：
   ```
   check → test → all teststatic test64        # --static 下 configure 重写，testshared 被移除
   teststatic: echo hello world | ./minigzip | ./minigzip -d && ./example
   test64:     echo hello world | ./minigzip64 | ./minigzip64 -d && ./example64
   ```
   结果：`*** zlib test OK ***` + `*** zlib 64-bit test OK ***`，**exit 0，全部通过**。
   完整日志: `logs/make-check.log`

5. **staging 安装**：`make install DESTDIR=stage/`，产物：`include/zlib.h zconf.h`、`lib/libz.a`、`lib/pkgconfig/zlib.pc`、`share/man/man3/zlib.3`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure CC=clang` 报 `unknown option ignored: CC=clang`，随后 `Missing or broken C compiler` | zlib configure 只认环境变量 CC，不认命令行参数 | CC 以环境变量传入：`CC=clang ./configure`（配方 conanfile.py 用 `CONFIG_SHELL=... CC="{cc}"` 前缀形式） |
| 2 | 系统同名库（R26）：OHOS SDK sysroot 自带 `/usr/lib/aarch64-linux-ohos/libz.so`，若发布 libz.so 会污染/冲突 | 系统库加载路径冲突（E541） | `--static` 静态编译，包内只含 `libz.a`，无 .so；已确认包内 0 个 .so |
| 3 | 静态 libz.a 非 PIC 则下游链不进共享库（E539/E541） | aarch64 下非 PIC 文本重定位不能进 DSO | `CFLAGS="-fPIC -O2"` 编译静态库；实测非-PIC libz.a 链 DSO 报 `R_AARCH64_ADR_PREL_PG_HI21`（logs/pic-probe-nopic-fail.log），PIC 版本链 DSO 成功且无 TEXTREL |
| 4 | test_package 里 `tools.build:readelf` conf 不存在 | 该 conf 不是 Conan 标准 conf（只有 compiler_executables 等） | readelf 是系统标准 binutils 工具（非编译器/编译标志，R33 不约束），直接调用 PATH 中的 `readelf` |
| 5 | 负向思考：zlib configure 默认注入 -fPIC，那显式 CFLAGS 是否多余？ | configure 行为可能随版本变化 | 显式 `CFLAGS="-fPIC -O2"` 保证任何环境确定性注入；已记录到 manifest knowledge_gained |

## 鸿蒙特有测试（R34 + E539/E541）

test_package 三层验证（真实调用被测包 API，非空壳）：

1. **`test.c`** → `test_probe`（静态链被测包 libz.a）：
   - `zlibVersion()` 校验 == "1.3.2"
   - `compress`/`uncompress` 往返 + 数据一致性
   - `compress2(Z_BEST_COMPRESSION)`/`uncompress2` 往返
   - `adler32`/`crc32` 校验和非零
   - `deflateInit`/`deflate(Z_FINISH)`/`inflateInit`/`inflate` 流式往返
   - `gzopen`/`gzwrite`/`gzread` gzip 文件往返
   - L1e 守卫：build() 显式校验被测包 includedirs/libdirs 存在（OHOS SDK sysroot 自带系统 zlib，防止破坏性负测试 fallback 到系统库）

2. **`pic_probe.c` + `probe_main.c`**（鸿蒙特有，E539/E541）：
   - 把被测包 `libz.a` 用 `clang -shared -fPIC` 链成 `libzpic_probe.so`
   - `readelf -d` 校验：无 TEXTREL ✅、NEEDED 无 libz.so（不拉系统同名库）✅
   - `probe_main` dlopen 该 .so，真实调用 zlib-backed `compress/uncompress` 往返并校验数据 ✅
   - 反面控制（判别力证明）：非-PIC libz.a 用同样命令链 DSO 直接失败
     （`R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol 'z_errmsg'; recompile with -fPIC`，
     见 logs/pic-probe-nopic-fail.log）

## 依赖版本

- 无 Conan 依赖（zlib 零外部依赖；仅使用系统 libc.so，由 clang 默认链入）
- 系统库引用：仅 libc.so（PIC 探针 DSO 实测 NEEDED 只含 libc.so）

## 验证结果

- `make check`（上游官方测试，R51）：teststatic + test64 全部通过，exit 0（2/2 组测试 OK）
- W3 `conan create`（profile ohos-aarch64，--build=missing）：**exit 0 完整通过**
  - 产物: `libz.a`（PIC）+ zlib.h/zconf.h + zlib.pc
  - test_package 三层测试全部 PASS（见 logs/conan-create.log）
- 包内无 .so，不污染系统 /lib、/lib64、/system/lib64、SDK sysroot（R26 合规）
- 已确认系统同名库证据：`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/lib/aarch64-linux-ohos/libz.so` 存在

## 源码修改

无补丁（patches/ 为空；仅构建旗标 CFLAGS="-fPIC -O2" + --static，见 conanfile.py）。
---

**编译结束**: 2026-09-24 23:16
**最终状态**: built
