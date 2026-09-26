# zlib 1.3.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-25（首次适配 2026-08-03，本次为完整复验重跑）
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 目标平台: HarmonyOS PC (os=OHOS arch=armv8)
- 状态: built

## 编译步骤

`CONFIG_SHELL=<bash> CC=clang CFLAGS="-fPIC -O2" ./configure --static --prefix=/` → `make -j1` → `make check`（全部通过）

conan 配方中编译器从 `tools.build:compiler_executables` conf 获取（R33），`CONFIG_SHELL` 取环境变量（默认
`/data/service/hnp/bin/bash`），`--static -fPIC` + `make -j1`（R9）+ `make check` 内置于 build()。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 沙箱内 `https://www.zlib.net` 被代理 MITM 拦截（证书 hostname 不匹配，返回 0 字节） | 沙箱网络代理对 zlib.net 的 HTTPS 处理异常 | 改用 `http://www.zlib.net` 下载（sha256 与官方一致），conandata.yml 仍保留官方 https URL（CI 环境可用） |
| 2 | 非-PIC libz.a 链进共享库报 R_AARCH64 relocation | configure 默认不加 -fPIC | 沿用 1.3.1.1 既有经验：CFLAGS=-fPIC 编静态库（同 1.3.1.1 配方） |

## 源码修改

无补丁（源码为官方 zlib 1.3.2，仅构建旗标 CFLAGS=-fPIC）。

## 依赖版本

- 无 conan 依赖（zlib 零外部依赖）

## 验证结果

- `make check`（上游官方测试）：minigzip 往返、example、minigzip64 往返、example64 全部 OK（"zlib test OK" + "zlib 64-bit test OK"，exit 0）
- conan-verify G0-G4 + L2/L4/L5 全部 PASS
- 真机 conan create + test_package 通过（test_probe 输出 `zlib 1.3.2 ok`）
- libz.a 已确认 PIC：可直接 `clang -shared -fPIC` 链进 .so（无 TEXTREL，仅依赖 libc.so）

## 消费者（系统同名库，静态 + PIC）

下游把 zlib 静态链进共享库（cairo/libpng/qpdf 等）时须 require `zlib/1.3.2`（-fPIC 静态库，不污染系统
/lib/libz.so*），沿用 1.3.1.1 的适配结论。

## 2026-09-25 完整复验（本次运行）

源码：`http://www.zlib.net/zlib-1.3.2.tar.gz`，sha256 `bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16`（与官方一致）。
（提示词给出的 `zlib.net/current/zlib.tar.gz` 在本机网络下 120s 仅拉到 217KB 即超时，改用官方版本化 URL。）

真实构建（`zlib-1.3.2.work`）：

```
CONFIG_SHELL=/data/service/hnp/bin/bash CC=clang CFLAGS="-fPIC -O2" ./configure --static --prefix=/   # rc=0
make -j1                                                                                             # rc=0
```

上游测试（全部实际执行，见 `reports/test-report.md`）：

| 命令 | 结果 |
|------|------|
| `make check`（= `test: all teststatic test64`） | rc=0，`*** zlib test OK ***` + `*** zlib 64-bit test OK ***` |
| `make teststatic`（minigzip 往返 + example 全功能） | rc=0 |
| `make test64`（minigzip64 往返 + example64） | rc=0 |
| `clang -fPIC -O2 -I. -o infcover test/infcover.c libz.a && ./infcover`（make check 之外的上游样例） | rc=0，76 条用例行 |
| `make testshared`（examplesh/minigzipsh） | rc=2 — `--static` 配置下 `test:` 已被 configure 改写为 `all teststatic test64`，无 libz.so，非本配置用例 |

用例统计：程序级 5/5 通过（4 项由 make check 驱动 + infcover），失败 0，跳过 0。

test_package（消费者视角）：`test_probe` 1/1 通过；鸿蒙特有测试 `test_ohos` 14/14 通过
（`test_ohos.c` + `ohos_pic_probe.c`：`__OHOS__` 编译期断言、`uname()` 识别 HarmonyOS、
deflate/inflate 与 compress2/uncompress 往返、crc32/adler32 标准向量、由静态 libz.a 编成的 .so
dlopen/dlsym —— 验证 libz.a 为 PIC，可被下游共享库吸收）。

门禁：conan create（`--build=zlib/1.3.2` 强制重建）rc=0；conan-verify G0–G4 + L2/L4/L5 全 PASS；
`finish` 的 W3 本地 CI 模拟（`ci/conan/build_and_test.sh`）PASS，`.ci-result.json` = `exit_code: 0`。

无源码补丁（`patches/` 为空）：configure 生成的 `Makefile`/`zconf.h` 属生成文件，按 R6 不生成补丁；
本次曾误生成 2 个由 configure 产生的伪补丁，已删除并把 `.work` 恢复为纯净源码树。

### 与制品仓的关系

制品仓已存在 `zlib/1.3.2#73f9291bbbf6587c1b453f541f5debf7`（配方与本归档 `conanfile.py`/`conandata.yml`
逐字节一致），二进制包 `6b129b068851896169fae42d399fa922d239ce8a` 亦可 `conan install` 消费。
本次变更**不涉及** `conanfile.py`/`conandata.yml`，故按 R37/L0j 保持版本号 `1.3.2` 不变；本次未执行 upload，
故 status 记 `built`。
---

**编译结束**: 2026-09-25 19:45
**最终状态**: built
