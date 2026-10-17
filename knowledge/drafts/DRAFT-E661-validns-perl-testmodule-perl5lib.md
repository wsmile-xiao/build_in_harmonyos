# DRAFT-E661 — 上游 make check 依赖非 core Perl 测试模块（validns 0.11.0 实例）

> 状态：草稿（等待人工/AI 审核后晋升 E661 正式条目，写 knowledge/graph/E661.kv +
> knowledge/doc/E661.md + graph/index.tsv 行）。结构化字段见同目录
> `DRAFT-E661-validns-perl-testmodule-perl5lib.kv`（已过 yaml.safe_load 回读、
> prescan_pattern re.compile、error_signature 正则编译三道硬性质量线）。

## 一句话

上游测试套件用 perl 写并 use 非 core 测试模块时，HarmonyOS PC 设备与 CI worker 的
系统 perl 都没有该模块；把 CPAN 官方发行物登记为 conandata 第二 source、构建期用
PERL5LIB（或 configure 的 `<MOD>_CFLAGS/_LIBS` 覆盖）注入，不改上游测试脚本本身。

## 命中的错误形态（engine 匹配面）

```text
Can't locate Test/Command/Simple.pm in @INC (you may need to install the Test::Command::Simple module)
BEGIN failed--compilation aborted at .../t/test.pl
Test Summary Report ... t/test.pl (Wstat: ... Tests: 1 Failed: 1)
Dubious, test returned 255
```

## 关键机理：缺模块的「优雅退化」是必败形态，不是可用降级

validns 0.11.0 的 `src/t/test.pl`：

```perl
use Test::More;
BEGIN { use_ok("Test::Command::Simple"); }
unless (*run{CODE})
{
	done_testing;
	exit(0);
}
```

- 模块缺失时 `use_ok` **不 die**（只记 1 条失败断言），随后 `unless (*run{CODE})`
  成立 → `done_testing` 把计划数定格为已运行的 1 条 → TAP 输出 `1..1 / not ok 1`。
- Test::Harness 判 `Dubious, 1/1 Failed` → `make check` rc≠0 → conan create 判负。
- 后果：看似「没模块就跳过整个套件」，实际是「套件整体失败」，且真实上游断言
  一条都没跑（TAP 分母 = 1）。

## 修复链（rec_approach 的展开）

1. **模块取源**：CPAN 官方发行物登记进 `conandata.yml` 的 sources 列表
   （示例：`https://www.cpan.org/authors/id/D/DM/DMCBRIDE/Test-Command-Simple-0.05.tar.gz`，
   sha256 `4d9dc422f03a620d0c441279f8366d1acf017da9acfdebe68b5a0e5c39c629da`）。
   R39 官方源口径不变；该 source 仅服务测试面，不进 `package()`。
2. **解包位置**：`source()` 里
   `get(self, **self.conan_data["sources"][1], strip_root=True, destination="test-perl")`
   —— 解到源码树旁的独立子目录，不混入上游源码。注意 `strip_root=True` 会把
   发行物目录名一并剥掉：模块树直接落在 `test-perl/lib/Test/Command/Simple.pm`。
3. **构建期注入**：`build()` 里

   ```python
   env = Environment()
   env.define("PERL5LIB", os.path.join(self.source_folder, "test-perl", "lib"))
   with env.vars(self).apply():
       autotools.make(target="check", args=["-j1"])
   ```

   上游脚本零改动（R7/R8：不打平台补丁进测试脚本）。
4. **禁用 conan perl**：conan 的 perl 包是 OHOS 交叉构建，同架构 build 机上
   dlopen 其 `Cwd.so` 失败（`Perl_my_cxt_init` 崩溃，device-facts §一.23），还会把
   PATH 里的系统 perl 顶掉。`make check` 用系统 perl：
   设备 `~/.harmonybrew/bin/perl`（5.44）/ CI worker `/data/service/hnp/bin/perl`
   （5.42），core `Test::Harness`/`Test::More` 两端实测可加载。
5. **显式降级分支**：`shutil.which("perl")` 不存在时打 warning、把 TAP 套件记为
   NOT_RUN、只跑上游的 C 自测程序——跳过必须留日志痕迹，禁止按 0 计数或写 PASS。
6. **计数口径**：TAP 断言数取 `t/test.pl` 的计划/结果行；三个 C 自测程序各取
   `All N tests successful.` 的 N；两者相加为上游 N′，与源码静态清点分开列报，
   四口径不混用。

## 预扫描（prescan）

- pattern：`\bCan't locate Test/\w+(::\w+)*\.pm in @INC|use Test::Command::Simple|libtest-command-simple-perl`
- globs：`*.pl, Makefile.am, conanfile.py, conandata.yml, notes.md`

## 设备可直接执行的验证（无 /tmp 依赖）

```sh
perl -MTest::Harness -MTest::More -e 1        # core 测试框架在
perl -MTest::Command::Simple -e 1             # 复现缺口（BEGIN failed）
# 修复后在任务目录：
#   conan create <配方目录> -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
#     -pr:b=<repo>/ci/conan/profiles/ohos-aarch64 --build=missing
#   日志应含 Test::Harness 的 Result: PASS 与三个 C 自测的 All N tests successful.
```

## 来源

- 任务：feat/validns-8.00.11.0（积分赛，首次适配）
- 实例日志：`$HOME/tmp/validns-8.00.11.0/conan-create-explore*.log`
- 关联既有条目：E007（config.guess/sub OHOS 识别，本任务以配方内补丁适配 2024 版
  config.sub 的三个新锚点，属 E007 的版本演化，不另立新条）
