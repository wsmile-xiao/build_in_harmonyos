# t1ha 2.1.4 — OHOS 适配笔记

## 概述

t1ha（Fast Positive Hash）是 Positive Technologies 出品的可移植非加密 64/128
位哈希库。上游主构建入口是仓库根的 raw `Makefile`（另有仅构建静态库、无安装
规则的 `meson.build`，作为子工程嵌入用）。本次为路径 A 基础适配：库源码零修
改，仅一条 tests-only 可移植性补丁。

- 上游：https://github.com/PositiveTechnologies/t1ha（tag v2.1.4，2020-10-07）
- 源码：GitHub tag 归档 `t1ha-2.1.4.tar.gz`
- SHA-256：`b3bc5bf5f337559b9d6f70e6bde1dec3854eb27f2aea51a147e69383fc6b05ef`
  （2026-09-09 macOS 与鸿蒙设备两端独立下载核对一致）
- 许可证：Zlib

## 构建方案

- 目标产物：`libt1ha.a` / `libt1ha.so` + 根目录单一公共头 `t1ha.h`。
- 上游对象统一以 `CFLAGS_LIB`（`-fPIC -fvisibility=hidden -Dt1ha_EXPORTS`）
  编译一次，再分别链接静态库与动态库；`libt1ha.so` 为真实文件（非版本化符号
  链接），无 OHOS 加载器符号链接问题。
- recipe 按选项只构建所需目标（shared → `libt1ha.so`，static →
  `libt1ha.a`），串行 make，CC/CXX 显式取自 profile 的
  `tools.build:compiler_executables`。
- `make check` 为上游测试入口；recipe 在原生运行时构建 `test` 并执行
  `./test --test-only`。

## 平台判定（为什么零平台补丁）

- Makefile 用编译器 target 串判定架构：aarch64-ohos 不命中 e2k/ia32 →
  `Target-ARCH: portable`（设备构建日志实测），AES-NI 相关对象不在编译清单。
- `t1ha.h` 的 `T1HA_USE_INDIRECT_FUNCTIONS`（GNU IFUNC）仅在
  `__ELF__ && __amd64__` 默认启用；aarch64 走 `__constructor__` 运行时
  解析，`t1ha0` 在 64 位小端机上解析为 `t1ha1_le`。
- `T1HA0_AESNI_AVAILABLE` 仅在 `__e2k__`/`__ia32__` 置 1，aarch64 为 0。

## 遇到的问题与解决方案

1. **tests/main.c 无效预处理指令 `#elseif`（上游笔误，唯一编译错误）**
   - 现象：设备原生构建在链接 `test` 阶段报
     `tests/main.c:119:2: error: invalid preprocessing directive, did you
     mean '#elif'? [-Werror,-Wunknown-directives]`，`make` 以 Error 2 退出。
   - 根因：`print_build_info` 内写成 `#elseif defined(__INTEL_COMPILER)`；
     标准 CPP 没有 `#elseif` 指令，clang（含 -Werror）直接拒绝。
   - 修复：补丁 `0001-fix-elseif-directive.patch` 将其改为 `#elif`，仅触及
     tests/main.c 一行，不影响库源码与测试逻辑。

2. **prescan PSCAN-GLIBC-001（medium）两处命中，均为安全分支解析**
   - `t1ha.h:254`：endian 头探测链首分支为 glibc；clang 恒定义
     `__BYTE_ORDER__`，整段块被跳过，musl 下无需任何分支。
   - `tests/mera.c:341`：基准的 CPU 亲和性设置在非 glibc 下走通用 POSIX
     回退，仅影响基准测量的绑核，不涉及正确性。
   - 结论：不修改。

3. **设备端 TLS 证书**
   - 设备全局 python3 直连 HTTPS 报 `CERTIFICATE_VERIFY_FAILED`；下载步骤
     设 `SSL_CERT_FILE` 指向设备上的 certifi cacert 后正常（见反馈文件，
     不属包配方范畴）。

## 验证结果

- 上游原生构建：clang 15 (hnp) 全部对象编译通过，`Target-ARCH: portable`。
- 上游测试：`./test --test-only` 12/12 通过（8 个 t1ha 条目 + 2 个
  HighwayHash + StadtX + wyhash；每条目内部约 81 个参考模式探针；AES-NI 与
  x86 变体在 aarch64 编译排除）。统计单位为 tests/main.c 的 verify() 条目，
  取数命令 `./test --test-only | grep -c '^Testing '`。
- Conan 干净构建 + test_package：12 项断言全部通过（先验证 `__OHOS__` 目标
  宏，确保原生消费者确为 HarmonyOS 目标；其余覆盖上游全量自检 API、跨平台
  已知答案向量、流式/一次性 128 位等价、确定性与种子敏感性）。
- 数字口径与最终设备日志一致；证据见 `reports/` 与 PR 正文。

## 本次为路径 A 基础适配

未修改上游库源码，无新增知识库扩展；补丁仅修复测试文件的一处笔误。
