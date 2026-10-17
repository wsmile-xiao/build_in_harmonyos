# libiksemel 1.4 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-09-18
- 编译器: clang/clang++
- 状态: built（待真机预检回填最终结论）

## 编译步骤

上游为经典 Autotools 工程，发布包自带 generated configure。
OHOS 适配采用零外部依赖配置，关闭 TLS 与 Python 绑定：

```bash
./configure --prefix=/ --without-openssl --without-gnutls --disable-python \
  --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos \
  --disable-shared --enable-static
make -j1
make -j1 check
make -j1 install DESTDIR=<package_folder>
```

test_package 采用直接编译的消费者视角验证（无 CMakeToolchain）：用 PATH 编译器直接编译 test.c 并运行，
覆盖对象栈、DOM 构建与序列化、SAX 回调、DOM 文档解析、
字符串工具、SHA-1、MD5、base64 编解码与 JID 解析。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 老版本 config.sub 不识别 aarch64-unknown-linux-ohos | 发布包自带的 config.sub 早于 OHOS 三元组，且严格 unified diff 上下文与古董文件空白不一致，conan 报 source file is different | 移除 0001 补丁，改用 build() 内 Python 容错编辑：锚定真机日志证实的 `# Here we must recognize` 行前插入 `*-*-linux-ohos` 早退分支 |
| 2 | configure 在 HMDFS 上创建临时目录权限不足 | autoconf 默认 umask 077，与 HMDFS 行为冲突 | 移除 0002 补丁，改用 Python 将 configure（源码与构建目录拷贝）内 `umask 077` 替换为 `umask 022` |
| 3 | configure Python 检测使用 Python2 语法 | configure.ac 内嵌 `print sys.prefix`，Python3 下必失败 | `--disable-python` 关闭 Python 绑定 |
| 4 | TLS 引入 OpenSSL/GnuTLS 外部依赖 | 上游 TLS 支持需要额外库，制品仓依赖链无收益 | `--without-openssl --without-gnutls` 关闭，纯解析功能不受影响 |
| 5 | 真机 configure 报 `/data/service/hnp/bin/bash: inaccessible` 且 `cannot run .../config.sub`（第 2 次同指纹） | 首轮仅用 isfile+X_OK 探测仍可能选中坏路径，且生成脚本/辅助脚本内硬编码坏路径未清理 | 改用 `cand -c true` 真实执行探测并将 profile 值排最后，build() 内对 configure/config.sub/config.guess/missing 及构建目录生成脚本做坏路径硬替换，env 仍覆盖 SHELL/CONFIG_SHELL |
| 8 | 真机 make install 失败：runtime install -c 未落盘 p//lib/libiksemel.a，随后 chmod 644 报 No such file（install_shim:true + hardlink:0 + chmod:0，8 个上游测试已 8/8 通过） | configure 探测的 install/toybox install 在 HMDFS 上不落盘，属 E182/E188 类文件系统子能力缺失，非测试失败 | build() 内新增 _write_install_shim/_redirect_install_to_shim/_make_chmod_tolerant（libbde/20240502 同构移植）：cp/mkdir 语义 shim + 改写各 Makefile 的 INSTALL + chmod 加 \|\| true（仅 HMBS_CAP_CHMOD=0 时），package() 补 TMPDIR 重探测；未改测试口径 |

| 9 | test_package exit 6 (SHA assert) + readonly_tmp hint | test.c strcmp on unterminated iks_sha/iks_md5 buffers (40/32 hex, no NUL) + expected RFC SHA (...0d4d) vs upstream 1.4 vector (...0d89d); make check 8/8 proves lib emits upstream value | test.c zero-init hash/md5, explicit NUL + strncmp 40/32 + stderr diagnostics, SHA expected aligned to upstream tst-sha.c (...0d89d); test_package conanfile build()/test() probe writable TMPDIR (HMBS TMPDIR else build-folder fallback) for compiler temps; no test skipped |

| 7 | 同指纹第 2 次仍报 `clang: inaccessible or not found`，且 config.log 中 CC 仍为旧封装路径 | 上轮经 `tc.environment()` 传 CC 未生效：AutotoolsToolchain 按 profile conf 渲染 CC，env 覆盖与 `os.environ` 均被忽略；且静态 `clang-N` 名猜测未覆盖该 worker 的 SDK 布局 | 改走执行期探测+生成文件改写+显式传参：generate() 保持 plain；build() 用 `--version` 真实试跑候选编译器并逐项打日志，改写生成工具链文件中的坏 CC/CXX，再以 `configure CC=.. CXX=..` 显式覆盖 |

## 源码修改

- patches/ 目录已清空（0001/0002 严格补丁因古董 config.sub/configure 上下文不匹配被移除）：config.sub 的 OHOS 三元组与 configure 的 umask 022 均改由 conanfile.py 内 Python 容错编辑完成
- 补丁均为构建适配，未改动库源码逻辑，未引入平台宏

## 依赖版本

本次适配无外部运行时依赖（conanfile 无 requires）。

## 验证结果

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

- 上游 `make check` 的 8 个测试程序（tst-ikstack/tst-iks/tst-sax/tst-dom/tst-sha/tst-md5/tst-filter/tst-jid）随 build() 执行
- test_package 编译并运行 test_libiksemel，覆盖 9 组断言场景
- 具体执行数与通过数以真机预检日志回填为准，本轮不预估数字

## 交付物

| 文件 | 说明 |
|------|------|
| archives/l/libiksemel/1.4/conanfile.py | Autotools 主配方 |
| archives/l/libiksemel/1.4/conandata.yml | 官方源码 URL 与 sha256 |
| archives/l/libiksemel/1.4/test_package/ | 真实调用库 API 的消费者测试 |
| archives/l/libiksemel/1.4/manifest.yaml | 版本级构建元信息 |
| archives/l/libiksemel/manifest.yaml | 软件级索引 |

## 注意事项

- 本库为纯解析库，不涉及图形、媒体、外设与系统底层接口，无深度适配项
- 如未来需要 TLS，需先适配并发布 OpenSSL 或 GnuTLS，再以新配方版本启用
- Python 绑定上游仅支持 Python2，已关闭，不纳入验证范围
