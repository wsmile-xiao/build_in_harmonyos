# future

[Future](https://metacpan.org/pod/Future) — 表示"等待完成的异步操作"的抽象
（promise/future 模式），是 Perl 异步生态的基础模块。

## 简介

Future 提供统一的异步结果占位与组合方式：`done`/`fail` 构造即时的成功或失败，
`then`/`else`/`followed_by` 串接依赖步骤，`wait_all`/`needs_all`/`wait_any`/
`needs_any` 合并控制流。配套模块：

| 模块 | 用途 |
|---|---|
| `Future` | 核心 future 对象与组合器 |
| `Future::Utils` | `call` / `repeat` / `fmap_concat` / `fmap_void` / `fmap_scalar` |
| `Future::Mutex` | 临界区串行化（`enter` / `available`） |
| `Future::Exception` | 异常对象封装 |
| `Test::Future` / `Test::Future::Deferred` | 测试辅助 |

`Future::PP` 是纯 Perl 实现；上游另提供可选的 XS 加速实现（`Future::XS`，
本发行版不含）。

## OHOS 适配

- **纯 Perl 模块**：无 XS、无 C/C++ 编译、无平台相关代码，行为与上游一致。
- **构建系统替换**：上游以 `Module::Build`（`Build.PL`）为构建系统，而 OHOS 环境
  不带该模块（设备 perl 5.42.2 与 `/data/service/hnp/bin/perl` 5.42.0 均无
  `Module/Build.pm`，制品仓也无 `perl-module-build` 制品）。配方在 `build()` 中
  用 perl 核心模块 `ExtUtils::MakeMaker` 生成**等价 Makefile.PL**（逐项转写上游
  `Build.PL` 的 `module_name`/`requires`/`test_requires`），随后
  `perl Makefile.PL INSTALLDIRS=site → make → make test → make install DESTDIR=<staging>`。
- **零补丁**：仅新增构建脚本，未改动任何上游源码，故 `patches: {}`。
- **打包**：`package_type = "python-require"`（纯 Perl 无二进制产物，无 bindirs
  → 无需 `commands.json`）；安装前缀随 perl 构建而异，`package()` 以遍历定位
  `Future.pm` 的方式确定 site 目录；`package_info()` 注入 `PERL5LIB` 供下游
  `use Future`。

## 依赖

运行时依赖全部为 perl 核心模块：`Carp >= 1.25`、`List::Util >= 1.29`、
`Test::Builder::Module`、`Time::HiRes`、`perl >= 5.014`；测试依赖
`Test2::V0 >= 0.000148`（OHOS perl 自带）。无 Conan 依赖。

## 功能验证

```bash
# 上游测试套件（56 文件 778 用例）
cd Future-0.52 && perl Makefile.PL INSTALLDIRS=site && make && make test
# → Files=56, Tests=778, Result: PASS

# 消费者验证（conan create 内 test_package，16 项断言）
conan create archives/f/future/0.52 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考

- 官网 / 文档: https://metacpan.org/pod/Future
- 发行版: https://metacpan.org/dist/Future
- 源码: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Future-0.52.tar.gz
