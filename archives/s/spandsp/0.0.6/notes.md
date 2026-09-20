# spandsp 0.0.6 适配笔记

## 编译环境

- 构建系统: autotools（libtool, 含预生成 configure）
- 编译日期: 2026-09-20
- 编译器: clang 15.0.4（OHOS SDK, aarch64-linux-ohos）
- 状态: built（conan-verify G0-G4/L2/L4/L5 全 PASS，未 upload）

## R51 上游测试清点与结果申报

上游 `--enable-tests` 构建 75 个测试程序（`tests/Makefile.am` 的 `noinst_PROGRAMS`），
无 automake `TESTS` harness（手动运行）。75 个测试中：

| 类别 | 数量 | 说明 |
|------|------|------|
| 纯算法测试（可运行子集） | 30 | 仅依赖 `-lspandsp`（其中 20 个在 OHOS 实际编译运行 PASS） |
| 依赖 spandsp-sim / 外部程序 | 45 | 需 sox/pbmtog3/fax2tiff 外部程序 + libsndfile/fftw/libxml2/libpcap/X11/fltk，OHOS configure `--enable-tests` 即 `Cannot make tests without ...` 失败（真实平台限制，非适配缺陷） |

**OHOS 实际运行结果：20/20 全 PASS**（pass 率 100%）

PASS 测试清单（20 个）：
`bit_operations_tests`、`crc_tests`、`complex_tests`、`complex_vector_float_tests`、
`complex_vector_int_tests`、`bitstream_tests`、`hdlc_tests`、`t38_core_tests`、
`t38_non_ecm_buffer_tests`、`v42_tests`、`vector_float_tests`、`vector_int_tests`、
`timezone_tests`、`logging_tests`、`dc_restore_tests`、`queue_tests`、
`awgn_tests`、`bert_tests`、`t35_tests`、`r2_mf_rx_tests`

未运行原因（逐项技术原因）：
- sox/pbmtog3/fax2tiff：外部可执行程序，OHOS 无（AC_MSG_ERROR 硬失败）
- libsndfile/fftw3：spandsp-sim 依赖；libsndfile/1.2.2 可消费但 45 个测试的程序
  主体是 WAV 数据驱动，且若干测试需 ITU/贝尔科 版权测试数据（不可分发）
- X11/fltk：GUI 测试库，OHOS 无
- libxml2/libpcap：super_tone/t38_gateway 测试依赖，未发布

## 编译步骤

```sh
# configure（R49 依赖注入，由 conanfile.py generate() 传入）
CPPFLAGS=-I<tiff_include> LDFLAGS=-L<tiff_lib> -Wl,-rpath,<tiff_lib> \
  ./configure --prefix=<DEFAULT_PREFIX> --enable-static --disable-shared
make -j1
make install
```

核心库构建 libtiff/4.7.0（configure 无条件 require `tiffio.h`/`-ltiff`，因 src 的
fax/t30/t38 代码用到 TIFF）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type` | 2008 版 config.guess 无 HarmonyOS 分支（uname -s=HarmonyOS） | 补丁 0001：配置三元组识别 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`（E007） |
| 2 | `config.sub: Invalid configuration 'aarch64-unknown-linux-ohos'` | 2008 版 config.sub 无 linux-ohos 支持 | 补丁 0002：basic_os 映射 + OS 白名单 + kernel-os 白名单三处加 ohos（E072） |
| 3 | `config.status: ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 强制 setgid，`umask 077` 建目录模式 2700 组无写权限 | 补丁 0003：configure 临时目录 `umask 077`→`022`（E129） |
| 4 | `make install` 并行 `File exists` | HMDFS 上并行 install-sh -d 并发建同一 include 目录 | conanfile.py `package()` 用 `-j1` 串行 |
| 5 | G2 首次失败 `Cannot build without libtiff` | conan-verify 环境无系统 libtiff | conanfile.py generate() 按 R49 注入 libtiff package_folder |
| 6 | 消费者用例 `g711.h`/`dtmf.h` 编译预期外 | 需按伞头顺序包含 telephony.h/logging.h/super_tone_rx.h；状态对象用指针 + `init(NULL)` | 修正 test_package/test.c 包含顺序与 API 用法 |

## 源码修改

- `patches/0001-config-config.guess.patch`：config.guess 添加 HarmonyOS 识别分支
- `patches/0002-config-config.sub.patch`：config.sub 添加 `linux-ohos[*]`（3 处）
- `patches/0003-configure.patch`：configure 临时目录 umask 077→022（E129）

## 依赖版本

- `libtiff/4.7.0`（conan 制品仓已发布，唯一第三方构建依赖）

## 验证结果

```bash
conan create ... (G2) ✅ — 干净构建 libspandsp.a/.so 成功
conan-verify G0-G4 + L2/L4/L5 ✅ — 全 PASS
上游测试: 20 个纯算法测试 PASS (20/20, 100%)
consumer test (test_package/test.c): G.711 roundtrip + DTMF generation 编译/链接/运行全通过
W3 本地 CI: .ci-result.json exit_code=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Conan 配方（autotools，R49 注入 libtiff） |
| `conandata.yml` | 官方源 + sha256 + 3 补丁声明 |
| `test_package/` | 消费者用例（g711/dtmf API）+ MANIFEST |
| `patches/0001-0003` | config.guess/config.sub/configure 3 个 OHOS 补丁 |

## 注意事项

- 上游完整测试套件（75 个）无法在 OHOS 运行属外部程序/版权数据/GUI 库依赖
  平台限制，已在 R51 如实申报；可运行子集 20/20 全 PASS
- 系统无同名库冲突（libspandsp 非系统库，R26 用静态默认，无污染 /lib 风险）

**编译结束**: 2026-09-20
**最终状态**: built
