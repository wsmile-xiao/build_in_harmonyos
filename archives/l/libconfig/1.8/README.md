# libconfig 1.8 (OHOS)

libconfig 1.8 — C/C++ 结构化配置文件解析库（main 已有 1.7.3，本目录为版本升级件）。

## 适配要点
- 上游 v1.8 无 release tarball，源码取 git tag archive
  （https://github.com/hyperrealm/libconfig/archive/refs/tags/v1.8.tar.gz，
  sha256 22e13253e652ec583ba0dd5b474bd9c7bd85dc724f2deb0d76a6299c421358ef）。
- tag archive 不带预生成 configure → build() 用 `autoreconf -f` 引导；
  刻意不用 `-fi`，避免 automake 覆盖 E007 补丁版 config.guess/config.sub。
- 构建工具：tool_requires automake/1.18 + libtool/2.5.4（CI 镜像无 automake）。
- OHOS 补丁：0001 config.guess 加 HarmonyOS 分支；0002 config.sub 接受
  linux-ohos 三元组。umask 077（E114）在 build() 对生成 configure 做文本修复。
- 交付静态库 libconfig.a / libconfig++.a（--enable-static --disable-shared），
  package_info 公开 C 库名 `config`。

## 测试
- 上游 tinytest 16/16（vendored 于 test_package 对安装库重跑；v1.8 新增 SettingLookups/ReadStream/BinaryAndHex）
- test_package：vendored 上游 16 用例 + 消费者 10 断言（1 ctest + 9 test.sh）
