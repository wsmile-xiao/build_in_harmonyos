# file-sharedir-install 0.14 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（上游自带 Makefile.PL / ExtUtils::MakeMaker）
- **编译日期**: 2026-09-18
- **平台**: arm64-ohos（OpenHarmony PC），perl 5.42.0（/data/service/hnp）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（未改动上游任何文件）

## 软件简介

File::ShareDir::Install 让 `Makefile.PL` 能声明并安装「共享数据文件」：
`install_share` / `delete_share` 登记 dist 级或模块级 share 目录，
`postamble` 把复制/删除规则注入生成的 Makefile，最终装到
`auto/share/{dist,module}/...`。单模块 `lib/File/ShareDir/Install.pm`，纯 Perl。

| 符号 | 导出 | 说明 |
|------|------|------|
| `install_share` | `@EXPORT` | 登记待安装的共享目录（dist / module）|
| `delete_share` | `@EXPORT` | 登记待删除的共享路径 |
| `postamble` | `@EXPORT_OK` | 供 `package MY;` 段调用以注入 Makefile 规则 |

## 编译步骤（conan create 全流程）

```bash
conan create archives/f/file-sharedir-install/0.14 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 File-ShareDir-Install-0.14）。

### 2. 构建（build()）

**本发行版自带 Makefile.PL**（由 Dist::Zilla::Plugin::MakeMaker 生成，直接
`use ExtUtils::MakeMaker`）——与 future / metrics-any / test-refcount 的
`Module::Build` 不同，**无需生成替代构建脚本**，也不涉及 Module::Build。
因此 build() 就是标准流程：

```
perl Makefile.PL INSTALLDIRS=site → make → make test → make install DESTDIR=<staging>
```

配方里对「源码根目录无 Makefile.PL」做了显式报错（而非静默降级），
避免上游换构建系统时悄然产出错误结果。

### 3. 打包（package()）
- 按登台树原样拷入 package_folder
- 以遍历定位 `File/ShareDir/Install.pm` 后**上溯两级**得到 site 目录
  （模块相对路径为 `File/ShareDir/Install.pm`，层级比 `Test/Refcount.pm` 更深；
  沿用 metrics-any / test-refcount 的教训，不可返回末级目录）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 裸 `prove -Ilib t/` 报 `All tests successful`，但只有 1 个用例 | t/10_makefile.t、t/11_dotfile.t、t/12_delete.t 均以 `plan skip_all if not -f 'Makefile'` 开头；裸 prove 下无 Makefile → 三个文件整体 skip（实测 Files=4, Tests=1）| 配方把 **`make test`** 放进 build()（Makefile 已生成）：Files=4, Tests=39 真跑 |
| 2 | 消费者脚本报 `String found where operator expected (Do you need to predeclare "install_share"?)` | 起初用运行期 `require` + `->import()` 导入 `install_share`，解析器在编译期不认识该裸字 | 改为编译期 `use File::ShareDir::Install;`（普通 Exporter 模块，直接用默认导出即可；注意与 Test::* 系的 `import => [...]` 需求相反）|
| 3 | 消费者脚本 `make -f consumer-Makefile` 报 `No rule to make target 'Makefile.PL'` | 生成的 Makefile 声明了 `consumer-Makefile: Makefile.PL` 依赖，而临时工作目录内没有 Makefile.PL | 在临时目录先写入一个等价的最小 Makefile.PL |

## 依赖

| 类型 | 依赖 | 状态 |
|---|---|---|
| runtime | Carp / Exporter / File::Spec / IO::Dir / strict / warnings | 均为 perl 核心模块，OHOS perl 内建 ✅ |
| configure | ExtUtils::MakeMaker | perl 核心 ✅（上游自带 Makefile.PL）|
| test | ExtUtils::MakeMaker / File::Path / File::Spec / Test::More | 核心模块 ✅ |
| Conan | 无 | — |

## 上游测试（R51 申报表）

| 项 | 内容 |
|---|---|
| 测试清点 | `t/` 目录 **4 个 .t 文件** |
| 运行方式 | **`make test`**（不可用裸 prove，见问题 #1）|
| 实测结果 | **Files=4, Tests=39, Result: PASS**，失败 0、skip 0 |
| 跳过项 | 无 |
| 是否入 build | **是**（`upstream_test_in_build: true`）|
| 上游测试改动 | **无**（原样运行）|

## 验证结果

```bash
# conan create（含 test_package R34 消费者验证）——rc=0
conan create archives/f/file-sharedir-install/0.14 -pr:h=... -pr:b=... --build=missing
file-sharedir-install/0.14: package(): Packaged 1 '.pm' file
...
ok 1 - File::ShareDir::Install version is 0.14
...（13 条断言）
OK: file-sharedir-install 0.14 python-driven consumer check
```

test_package 消费者测试覆盖（13 条，全过）：版本号；三个接口齐备；非法
share 类型必须 confess；`install_share` 登记 dist/module 两类；生成的 Makefile
含 per-dist 与 per-module 目标且默认排除隐藏文件；**真实执行 make** 后
blib 内 dist/module 共享文件齐备（含**含空格文件名**正确复制、隐藏文件确实
未被复制、模块子目录内的文件正确落位）。

## 注意事项

- 纯 Perl 包不涉及交叉编译工具链；`make` 使用宿主 perl 即可。
- 解释器固定 `/data/service/hnp/bin/perl`（5.42.0）。
- 上游 `xt/` 目录是 **author/release 测试**（Pod 拼写、EOL、kwalitee 等），
  依赖大量非核心模块，`make test` 不会执行它们（只跑 `t/*.t`），本适配亦不涉及。
- 消费者脚本会生成临时 Makefile 并在独立临时目录内执行 make，测试结束自动清理。

## 对话记录

### 对话 #1（2026-09-18）

- 在鸿蒙 aarch64 设备上完成适配：`conan create` 通过。
- 上游测试真实运行：t/ 4 文件 39 用例全过，无 skip（经 `make test`）。
- 消费者测试 13/13 通过，覆盖「登记共享目录 → 生成 Makefile → make →
  校验 blib 产物」的完整消费者语义。
- 零补丁：上游自带 Makefile.PL，未改动任何上游文件。
- 本次三处实测教训已记入 knowledge_gained：①构建系统须实地确认（本包是
  Makefile.PL 而非 Module::Build）；②`skip_all if not -f 'Makefile'` 类测试
  必须走 make test，否则假绿；③模块路径更深时 site 目录需逐级上溯。
---

**编译结束**: 2026-09-18 05:00
**最终状态**: built
