# lzsa 1.4.1 — 适配记录

> 分支: feat/lzsa-1.4.1
> 最后更新: 2026-08-13

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | lzsa |
| 版本 | 1.4.1 |
| 状态 | built（待真机预检复核） |
| 构建系统 | makefile |
| 源码 URL | https://github.com/emmanuel-marty/lzsa/archive/refs/tags/1.4.1.tar.gz |
| sha256 | c65ca1e6a43696f4ca5edc2c98229fba1044806bd21bc2a8ce4b867dc9cfc45c |
| 依赖 | 无 |
| 许可 | CC0-1.0（代码）, Zlib（divsufsort） |
| 包类型 | application（命令行工具，R38: 软件级 commands.json 已声明） |
| 产物 | 仅 CLI（Makefile 无 lib/.a/.so 目标, cpp_info.libs=[]） |

## 二、上游测试套件审计（hmbs 机器证据门禁）
审计对象: 官方源码包 lzsa-1.4.1.tar.gz（2026-08-13 下载，sha256 与 GitHub 一致）
- Makefile 定义 test 目标: `./lzsa -test`（内置自测, 二进制内含压缩/解压往返校验代码）
- 无独立 tests/ 目录; 全树 find -name '*test*' 仅命中 Makefile test 目标 + lzsa -test 命令行选项
- 无 TESTS/check_PROGRAMS/check-local 目标; 无 make check 目标
- 无 gtest/pytest/cmake ctest 测试框架
结论: 上游 lzsa 1.4.1 存在内置自测 (`lzsa -test`), test_package/MANIFEST.yml 声明
`upstream_tests_exist: true`; 自测在 test_package/test_lzsa.sh 中真实执行。
功能验证由 test_package 真实执行 lzsa 二进制完成（-test 自测 + 格式2/格式1
压缩/解压往返内容比对），详见 test_package/MANIFEST.yml。

## 三、补丁清单
| 补丁 | 内容 | 类型 |
|------|------|------|
| （无） | 零补丁: 上游 Makefile 使用 CC=clang / CFLAGS=... 简单 = 赋值, 命令行可覆盖 | — |

补丁来源: 无需补丁。上游 Makefile 无硬编码平台/路径, config.guess/config.sub 不适用
（非 autotools 项目）。CC= 通过 make 命令行显式传入 OHOS arm64 clang, 命令行赋值
优先于 Makefile 内 = 赋值。

## 四、配方要点（conanfile.py）
- 纯 Makefile 构建: build() 直接 `make -j1 CC="..." CFLAGS="..." LDFLAGS=""`
- CC 解析: 优先 $CC 环境变量, 其次 /data/service/hnp/bin/clang, 最后 fallback `clang`
- CFLAGS 覆盖: -O3 -Isrc/libdivsufsort/include -Isrc（丢弃 -fomit-frame-pointer）
- make -j1（R9/E074: 并行 make 在 HMDFS jobserver FIFO 上 EPERM）
- package_type=application, cpp_info.bindirs=["bin"], cpp_info.libs=[]
- 零补丁: source() 仅 get() + strip_root, 无 patch 应用

## 五、验证记录
- 本机: 源码下载 + sha256 校验通过; Makefile CC/CFLAGS 命令行覆盖验证通过
- 真机: 待 HMBS 预检（conan create + test_package + 上游测试审计门禁）
- 预检通过后由 HMBS 统一提交、推送并创建 PR，正文测试表以真机 evidence 为准

### 真机预检轮次
- 第 1 轮（2026-08-13，pending）: 等待 HMBS 预检。配方已就绪: 零补丁 Makefile 构建,
  CC= 通过命令行覆盖, test_package 执行 4 个真实断言（-test 自测 + 格式2/格式1 往返
  cmp + 压缩率健全性检查）。
  状态: 工作树未提交，等待 HMBS 预检。

## 六、遗留问题
- 无已知编译阻塞; 无外部依赖（纯 C + 静态链接 divsufsort）
