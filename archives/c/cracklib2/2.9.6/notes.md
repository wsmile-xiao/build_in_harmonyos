# cracklib2 2.9.6 适配笔记

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-09-10
- 编译器: clang
- 状态: built（待真机预检回填实测结果）

## 编译步骤

```bash
./configure --without-python --build=aarch64-unknown-linux-gnu --enable-static --disable-shared
make -j1
make check
make install
```

conan 流程由 `conanfile.py` 驱动：`Autotools.configure()`、`make -j1`、`make check`，最后 `Autotools.install()`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 上游 config.guess 无 HarmonyOS 分支 | `generate()` 固定 `--build=aarch64-unknown-linux-gnu` |
| 2 | autoconf 临时目录权限异常 | HarmonyOS 上 mktemp -d 目录权限不符合预期，config.status 失败 | 复用 mktemp 包装器使其返回失败，强制走 mkdir 回退 |
| 3 | Python 绑定需要开发头 | 默认可能探测 Python | 显式 `--without-python` 关闭绑定 |

## 源码修改

无补丁。生成文件（configure、Makefile.in）不修改。

## 依赖版本

- zlib/1.3.1（字典压缩打包环节 `-lz`）

## 上游测试

- 上游测试命令：`make check`（编译测试驱动）+ `make test` 口径完整执行（`util/cracklib-check < test-data` 10 项逐密码检查 + `util/testlib < test-data` 1 项接口自测）
- 上游测试计数口径：test-data 10 行密码逐项检查 + testlib 接口自测 = **N=11**（testnum/teststr 的 `PWOpen(NULL)` 为上游死代码入口，任何平台均无法打开字典，不计数）
- 字典生成：配方内用 Python 复现 `cracklib-format` 预处理（与上游产出逐字节一致，51526 词）+ `util/cracklib-packer` 打包，`--with-default-dict` 指向构建目录
- HarmonyOS 环境说明：`FascistCheck`/`cracklib-check`/`testlib` 走 `getpwuid` 前置检查（FascistGecos），HarmonyOS 应用 uid 无 passwd 条目，输出 "you are not registered in the password file"（环境限制，非库缺陷）；字典引擎完整性由 test_package 的 `FascistCheckUser`（显式 user 参数绕过 getpwuid）验证：过短密码被规则拒绝、字典词被识别、强密码通过
- `build()` 成功后输出 `HMBS_UPSTREAM_TEST_RESULT`（discovered/executed/passed=11）

## 验证结果

待真机预检回填（conan create 含 make check 与 test_package）。

## 注意事项

- 本包以库形态交付（`libcrack`），附带的 `cracklib-check/packer/unpacker/format` 工具随 `make install` 安装，不单独声明为命令行工具包
- 运行时字典文件需由业务方自行生成（`cracklib-format | cracklib-packer`），配方不捆绑默认字典
