# ocl-icd 2.3.4 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

1. **源码下载**: 使用 curl 下载源码包（Python urllib 因 SSL 超时失败），手动放入 `~/tmp/builds/ocl-icd-2.3.4.tar.gz` 后执行 `ohc-run.py init-build`
2. **autoreconf 生成 configure**: 原始 tarball 不包含预生成的 configure 脚本，需先运行 `autoreconf -vi -Wall` 生成
3. **configure**: `./configure --prefix=$DEFAULT_PREFIX` — 正常检测平台 `aarch64-unknown-linux-ohos`，检测到使用内部 OpenCL 头文件，检测到 libdl
4. **修补 config.status**: configure 生成的 config.status 因 HMDFS 限制无法在当前目录创建临时文件，需修补：
   - 将 `umask 077 && mktemp -d "./confXXXXXX"` 替换为 `mktemp -d "$TMPDIR/ocl-icd-config-tmp/confXXXXXX"`
   - 将 `tmp=./conf$$-$RANDOM` 替换为 `tmp=$TMPDIR/ocl-icd-config-tmp/conf$$-$RANDOM`
   - 移除 `umask 077` 限制
   - 修补后运行 `./config.status` 成功
5. **make**: `make -j1` 编译成功，生成 libOpenCL.so.1.0.0、cllayerinfo、libdummycl 等
6. **make install DESTDIR**: `make install DESTDIR=$TEST_PREFIX` 成功安装到 staging 目录
7. **make check**: 全部 31 个测试通过
8. **make install**: `make install` 不带 DESTDIR，安装到 $DEFAULT_PREFIX 用于本地验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 无法创建临时文件 Permission denied | HMDFS 上 umask 077 创建的目录无法写入文件（E090） | 修补 config.status，将临时目录路径改为 $TMPDIR 子目录 |
| 2 | 原始 tarball 缺少 configure 脚本 | ocl-icd 只分发 configure.ac，不包含预生成 configure | 运行 `autoreconf -vi -Wall` 生成 |
| 3 | G4 门禁 FAIL: manifest 缺少 build_system | verify_build.py 检查顶层 build_system 字段 | 添加顶层 `build_system: autotools` |
| 4 | G4 门禁 FAIL: 无二进制文件 | DESTDIR 模式下文件在 $TEST_PREFIX/$DEFAULT_PREFIX/ | 使用 `--install-prefix` 指定正确路径 |

## 源码修改

无源码文件修改。仅修补了 configure 生成的 config.status 脚本（属于生成文件修补，非源码修改）。
R6 合规：无源文件变更，无需 track-edit。

## 依赖版本

无外部依赖。仅依赖系统 libdl（libc 内置）。

## 验证结果

- make check: **31/31 tests PASS**（详见 reports/test-report.md）
- cllayerinfo 二进制已安装到 $DEFAULT_PREFIX/bin/ 并可执行
- libOpenCL.so.1.0.0 共享库已安装到 $DEFAULT_PREFIX/lib/
- pkg-config: OpenCL 3.0 版本信息正确
- ocl_icd.h 头文件已安装到 $DEFAULT_PREFIX/include/

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ocl-icd-2.3.4-ohos-aarch64.tar.gz | 1026KB | 预编译包（含ELF签名、strip、RPATH） |
| ocl-icd-2.3.4-ohos-aarch64-debug.tar.gz | 270KB | 调试符号包 |
| libOpenCL.so.1.0.0 | 236KB | OpenCL ICD Loader 共享库 |
| cllayerinfo | 228KB | ICD 层信息查询工具 |
| ocl_icd.h | 58KB | OpenCL ICD 头文件 |
| OpenCL.pc / ocl-icd.pc | 278/297B | pkg-config 文件 |

## 注意事项

- ocl-icd 是纯 C 项目，使用 Ruby 脚本生成 OpenCL API 绑定代码（icl_generator.rb）
- config.status 的 HMDFS 临时目录问题需要每次 configure 后手动修补（E090 知识条目已记录）
- 原始 tarball 需 autoreconf 预处理，hints/pre-configure.sh 已创建
- 该软件不需要真实 OpenCL 驻动即可编译和测试（内置 dummy ICD）
- cllayerinfo 工具不支持 --version 参数（设计如此），G2 功能门禁中为 ⚠️ 而非 ❌

## 质量门禁

| 门禁 | 结果 | 说明 |
|------|------|------|
| G0 干净构建 | PASS（手动验证） | 需 autoreconf + config.status HMDFS 修补 |
| G1 二进制完整性 | PASS (✅4 ⚠️0 ❌0) | 4个 ELF 产物全部有效 |
| G2 功能可用性 | PASS (✅0 ⚠️1 ❌0) | cllayerinfo 不支持 --version |
| G3 可移植性 | PASS (✅0 ⚠️2 ❌0) | RPATH/签名警告 |
| G4 档案完整性 | PASS (✅0 ⚠️0 ❌0) | manifest+notes+reports 完整 |

---

**编译结束**: 2026-06-11
**最终状态**: published