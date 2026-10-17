# zita-lrx 0.1.2 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，source/Makefile，无 configure 脚本）
- 编译日期: 2026-10-02
- 编译器: /data/service/hnp/bin/clang++（OHOS clang 15, aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

纯 Makefile 项目，无 configure。在 `source/` 目录执行：

```bash
make -C source -j1 \
  CXX=<conan profile 的 tools.build:compiler_executables.cpp> \
  PCONFCFL="-I. -DCLTHREADS_NO_PTHREAD_CANCEL -I<clthreads>/include -I<jack>/include" \
  LDFLAGS="-L<clthreads>/lib -L<jack>/lib" \
  all

make -C source install PREFIX=/ DESTDIR=$package_folder
```

PCONFCFL 说明：Makefile 命令行覆写 CPPFLAGS 会丢上游自己的 `-DVERSION` 定义，补丁在
CPPFLAGS 追加 `$(PCONFCFL)` 槽位，配方经它注入依赖 include 路径与 OHOS 宏，上游定义不动。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 硬编码 `CXXFLAGS += -march=native` | 上游为本地优化编写，交叉构建不安全 | 补丁移除该行，优化标志由 Conan profile 控制 |
| 2 | 命令行覆写 CPPFLAGS 会丢 `-DVERSION` | make 命令行变量优先级最高 | 补丁新增 `$(PCONFCFL)` 槽位（追加进 CPPFLAGS），配方经它注入 include 路径 |
| 3 | clthreads 在 OHOS 需要 `CLTHREADS_NO_PTHREAD_CANCEL`（musl/OHOS 无 `pthread_cancel`） | clthreads 的 `package_info()` 只对 CMakeDeps 消费者生效，本包是裸 make 构建 | `build()` 内当 `settings.os == OHOS` 时把宏拼进 `PCONFCFL`（同 jaaa/aliki/aeolus 先例） |
| 4 | 上游 `install` 规则用裸 `install` 命令 | 非登录 PATH 下无裸 `install`，打包步骤不可依赖 | 补丁引入 `INSTALL ?= /bin/install`（toybox），绝对路径默认值 |
| 5 | 构建主机无 JACK 服务、无音频硬件：zita-lrx 是 JACK 实时客户端 | 平台没有运行中的 jackd | 消费者测试分三层并逐条打印机器可读判决：产物层 4 条（ELF 机器码 AArch64 / DT_NEEDED 全是裸 soname / `.codesign` 段数=1 / 二进制内无宿主前缀 /usr/local）、装载解析层 3 条（`-h` 横幅 exit 1 / 无参 exit 1 / 缺配置文件 "Can't load configuration" exit 1）、能力层（合法配置解析到 Jclient 构造、边界签名 "Can't connect to JACK" exit 1，实时 DSP 路径声明 SKIP）——**没有把不可执行记成通过** |
| 6 | `conan create` 跑测试时会把 `test_package/runtime-libs`、`staged-bin`、`smoke-work` 落在归档树内 | test_package 以 `self.build_folder` 派生路径 | 出厂前 `rm -rf` 清理（每次测试会重建），跑完回读 `git status` 二次确认归档内无二进制 |
| 7 | OHOS musl 加载器对 `libc++_shared.so` 不从默认路径解析 | 本机 ldso 实测：bare 运行 127，`LD_LIBRARY_PATH=/system/lib64` 可跑 | test() 里 `LD_LIBRARY_PATH` 前置 `/system/lib64`（staged 闭包 + 系统运行时兜底） |

## 源码修改

- `patches/0001-source-Makefile.patch`：移除 -march=native；CPPFLAGS 追加 $(PCONFCFL) 注入槽；
  INSTALL 参数化（默认 /bin/install）。仅 Makefile 一处，不动任何 .cc/.h。

## 依赖版本

- clthreads/2.4.0、jack/1.9.22（制品仓 ohpcd 均已发布，`conan list` 已验证）
- 版本选择说明：仓内 9 个 clthreads 消费者全部用 2.4.0（aliki/aeolus/jaaa 等），
  跟随生态约定保持一致，避免混版本闭包。

## 验证结果

- 编译：`zita-lrx` ELF64/AArch64 可执行文件生成成功，DT_NEEDED 全裸 soname
  （libclthreads.so / libjack.so / libc++_shared.so / libc.so / librt-so / libm 等）
- 上游测试：无（`make -C source check` → "No rule to make target 'check'"），已如实声明
- 消费者测试（test_package）：三层 8 用例全过 + 1 SKIP（realtime-dsp 无 JACK 音频图）
  - 产物层：AArch64 ✅ / DT_NEEDED 裸 soname ✅ / .codesign=1 ✅ / 无 /usr/local 前缀 ✅
  - 装载层：`-h` 横幅 "zita-lrx-0.1.2" exit 1 ✅ / 无参 exit 1 ✅ / 缺配置 "Can't load configuration" exit 1 ✅
  - 能力层：合法配置全语法解析 → Jclient 构造 → "Can't connect to JACK" exit 1 ✅（边界签名断言）；realtime-dsp SKIP（带原因）
- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64` 本地验证通过

## 上游 URL 定位说明（本任务特有）

- 官方域为 kokkinizita.**linuxaudio.org**（.net 变体直探全 404，不是官方站）。
- 三重佐证：①同族 libzita-resampler 1.11.2 conandata（本仓 main）用同域同目录；
  ②Debian sources zita-lrx 0.1.2-1 的 debian/watch 指向
  http://kokkinizita.linuxaudio.org/linuxaudio/downloads/index.html（文件名模式 zita-lrx-(.*)\.tar.bz2）；
  ③实测 https://kokkinizita.linuxaudio.org/linuxaudio/downloads/zita-lrx-0.1.2.tar.bz2
  HTTP 200（21838 字节，application/x-bzip2，Last-Modified 2018-08-25）。
- sha256=54740dc563ffb3f0a26aabd20dc6905f42a4e77dfb80ae71c3a2899eb8418c97（官方源直下实测）

## 注意事项

- zita-lrx 是 JACK 实时客户端，运行需要 jackd 与音频硬件；OHOS/CI 无这些设施，
  测试以「加载完整闭包 + 配置解析全语法 + 到达 JACK 服务边界」为通过标准。
- conandata.yml sources.url 为官方源（R39：单条官方 URL，不手动加镜像）。
- 分支：feat/zita-lrx-0.1.2（平台任务 #12381，认领人 calbee21）。

---

**编译结束**: 2026-10-02
**最终状态**: built
