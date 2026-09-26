# audioresamplerate 2.1 适配笔记

## 编译环境
- 构建系统: makefile（顶层 Makefile：`make iniparser/log/resamplerate/all`）
- 编译日期: 2026-09-24
- 编译器: clang 15.0.4（OHOS aarch64 profile，`/data/service/hnp/bin/clang`）
- 状态: built（本地 conan create 通过，测试 1/1 PASS）

## 编译步骤

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

配方 build()：
1. `make clean cleanso` 清除上游 tarball 自带的 x86-64 预编译 .so（必须从源码重建目标架构）
2. `mkdir -p bin`（上游 Makefile 不自动建 bin/ 目录，`make all` 链接时 ld 会因输出目录缺失失败）
3. `make iniparser`、`make log`、`make resamplerate` 依次构建三个共享库
4. `make all` 链接 bin/resamplerate

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 tarball 自带 x86-64 预编译 lib/*.so，aarch64 链接报 incompatible | 上游仓库把构建产物提交进源码树 | 配方 build() 先 `make clean cleanso` 删除，全部从源码重编 |
| 2 | `make all` 报 `ld: cannot open output file bin/resamplerate: No such file or directory` | 上游 Makefile 不创建 bin/ 目录 | 配方 build() 先 `mkdir -p bin` |
| 3 | init-build 默认按 autotools 生成配方模板，与纯 Makefile 构建不符 | conan-init 构建系统猜测与 URL/目录推断 | 手工重写 conanfile.py 为纯 Makefile 构建（无 configure/autotools） |
| 4 | conan source() 报 `BadZipFile: File is not a zip file` | codeload tar.gz 端点 URL 无 .tar.gz 后缀，conan get() 默认按 zip 解压 | conandata.yml 显式声明 `filename: audioresamplerate-2.1.tar.gz` |
| 5 | float_cast.h 警告 "Don't have lrint()/lrintf()" | 上游为缺失 lrint 的旧平台准备的回退分支 | 仅警告，自动回退标准 C 转换，功能正常，不影响构建 |

## 源码修改

无补丁（patches/ 为空）。构建入口修正（bin/ 目录、清除预编译 .so）全部在 conanfile.py 配方内完成，
不对上游源码改动。

## 依赖版本

无 runtime/tool 依赖（纯 C，仅 libc；libresamplerate = Secret Rabbit Code 0.1.8 移植 + iniparser 移植）。

## 验证结果

```bash
# conan create（含 test_package）
100% tests passed, 0 tests failed out of 1   # test_audioresamplerate PASS

# 消费者用例（consumer/consumer_audioresamplerate.c）
consumer_audioresamplerate: PASS   # src_new/src_process 16k->48k, 4799 帧, energy=99.11

# 鸿蒙专项测试（consumer/ohos_test_audioresamplerate.c）
ohos_test_audioresamplerate: PASS   # 小端平台自检 + 5 转换器枚举 + 2399 帧输出校验

# 上游 CLI 自然运行（./bin/resamplerate）
退出码 0，stdout "output path : ./audio/out.pcm / successfully"
```

上游测试：官方 v2.1 无任何测试声明（source_declared_total=0），详见表 single 台账
reports/upstream-test-ledger.md。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 纯 Makefile 构建配方，3 个共享库 + bin/resamplerate + 头文件 |
| conandata.yml | 官方 codeload 源，SHA-256 68000577…fb808a |
| test_package/ | CMake 消费者测试 test.c（src_simple 16k->48k 校验） |
| consumer/ | consumer_audioresamplerate.c + ohos_test_audioresamplerate.c |

## 注意事项

- 上游 Makefile `CC := gcc` 硬编码：配方显式传 `CC=clang`（来自 OHOS profile 工具链）；
  不得裸用 shell 环境变量（R33）。
- 库为 GPL-3.0（含 Secret Rabbit Code 移植与 iniparser 移植组件）。
---

**编译结束**: 2026-09-24 09:44
**最终状态**: built
