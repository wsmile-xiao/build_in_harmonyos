# pit 0.1.0 — 适配笔记

> 创建时间：2026-09-17
> 适配者：Bingggooo（队伍：来都来了）
> 上游：https://github.com/michaeldv/pit（tag 0.1.0）
> 源码包 sha256：ddf78b2734c6dd3967ce215291c3f2e48030e0f3033b568eb080a22f041c7a0e
> （与 Homebrew formula 及 FreshPorts 记录交叉确认一致）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | pit |
| 版本 | 0.1.0 |
| 构建系统 | makefile（裸 Makefile，无 configure） |
| 产物类型 | 单个可执行文件 `pit`（application） |
| 依赖 | 无（纯 C + 系统 libc；测试需系统 Ruby） |
| 补丁 | 无（零补丁构建） |

## 二、上游审计

- 源码布局：`src/*.c` 11 个文件（action/args/db/help/note/format/pit/project/table/task/util）
  + `src/*.h`、test/`pit_test.rb`、`tools/commit-msg`、`Makefile`、`LICENSE`、`README.md`
- 构建目标：`make` 生成 `bin/pit`；`make test` 运行 `./test/pit_test.rb`（Ruby 套件）后清理
  `test/test.pitfile`；`make install` 直接 `cp` 到 `$(PREFIX)/bin`（无 DESTDIR）
- 测试框架：Ruby（`test/pit_test.rb`），用例数为 Test::Unit 实跑输出解析，不硬编码
- 本机因出站网络受限无法下载源码包，URL/sha256 采用 Homebrew 与 FreshPorts 双源交叉确认；
  真机预检的 `get()` 下载 + sha256 校验即第三方权威验证

## 三、配方设计

- `build()`：`make CC=<conf 注入的 clang> -j1`，随后 `_run_upstream_tests()` 运行 `make test`
  - Ruby 查找顺序：PATH 中的 `ruby`，回退 `/data/service/hnp/bin/ruby`（pandocomatic 已证实真机存在）
  - 输出重定向到 `upstream_test.log` 后回显，保证 conan 日志保留完整证据
  - 解析 Test::Unit 的 `N tests, M assertions, F failures, E errors`，退出码与解析结果双重判定
  -  verdict 写入 `upstream_test_result.json`，`package()` 复制到包内 `res/`，test.sh 原样重放
    为 `HMBS_UPSTREAM_TEST_RESULT`（dav2d 模式，缓存命中依然有证据）
- `package()`：直接打包 `bin/pit`（绕过无 DESTDIR 的 install 目标）+ `LICENSE*` + 上游测试 verdict
- `test_package/test.sh`：9 个消费者功能断言，全部 grep 本轮创建的唯一字符串
  （`OHOS pit test ...`），空 fixture 无法蒙混；PITFILE 相对路径 + 只断言输出内容，
  主动规避上游 0.1.0 的绝对路径段错误与成功退出码为 1 两个已知 quirks（详见 README）
- HMBS 标记：`test.sh` 末尾输出带 `discovered`/`passedCount` 的
  `HMBS_TEST_PACKAGE_RESULT`，并重放包内 verdict 为 `HMBS_UPSTREAM_TEST_RESULT`

## 四、风险与已知限制

- 上游 0.1.0 之后的上游修复（PREFIX 安装、绝对路径段错误、成功退出码）刻意未 backport，
  保持零补丁与上游行为一致；如 CI/真人要求，再补丁跟进
- `pit` 显示的用户名来自系统用户查询，真机/CI 用户名不同只影响装饰性输出，不影响断言

## 五、验证记录（待真机预检回填）

- `conan create`（含上游 Ruby 套件 + test.sh 9 断言）：待 HMBS 真机预检
- `HMBS_TEST_PACKAGE_RESULT` / `HMBS_UPSTREAM_TEST_RESULT`：待预检日志摘录

## 六、2026-09-17 真机失败修复（test_package 阶段）

- 现象：预检 `test.sh [test 3/9] pit init` 报
  `pit (fatal): no username?! - No such file or directory`，建库失败导致后 6 个
  断言连带失败（`test.pit - No such file`），`discovered:9/passedCount:2`。
- 根因：`src/util.c:current_user()` 只认 `getpwuid(geteuid())`；HarmonyOS PC
  真机（HNP conan 构建用户）在 passwd 库中无对应条目，`getpwuid` 返回 NULL，
  旧代码直接 `perish("no username?!")`，于是 `pit init`（经 `write_header` /
  `pit_action`）及所有读写库命令全部 fatal。上游 Ruby 套件的 `match failed`
  同样源于库从未建成，而非日期解析 bug。
- 修复 1（补丁 `patches/0001-current_user-fallback.patch`，已在 conandata 注册）：
  `getpwuid` 成功仍用系统用户名；失败时按 `$USER` → `$LOGNAME` →
  `getlogin()` → 字面 `ohos` 回退，保证返回非空稳定用户名。上游断言只用
  `\(.+\)` 匹配用户名，任意回退名均可通过；test.sh 断言只 grep 自建字符串，
  不受用户名取值影响。
- 修复 2（`conanfile.py:_run_upstream_tests` 诚实计数）：上游 tiny_should
  成功打印 '.'、失败只打印 `match/equal failed` 且退出码恒 0，旧的
  “无 Test::Unit 摘要则按退出码判 1/1 通过”分支把失败误报为通过（本轮日志即
  含多条 match failed 却打出 `passed` 标记）。现改为用计数包装 load 同一
  `test/pit_test.rb` 全量运行（拦截 `print '.'` 计成功、`Hand#oops` 计失败，
  零断言删减），输出 `HMBS_UPSTREAM_SUMMARY passed=N failed=M` 并在失败时以
  非零退出；配方取计数与失败行数的较大值作为 failed，未知输出一律判失败，
  杜绝假通过。
- 待下轮预检验证：上游套件全绿 + test.sh 9/9。

## 七、2026-09-17 真机失败修复（补丁解析失败）
- 现象：conan create 在 build() 的 apply_conandata_patches 直接失败，
  ConanException: Failed to parse patch patches/0001-current_user-fallback.patch，
  前有 WARN extra lines for hunk no.1 / finished with errors。
- 根因：补丁 hunk 头 @@ -60,12 +60,25 与正文实际行数不符（含 printa 上下文行，
  旧行应为 14 左右而非 12），Conan 严格解析器拒绝容错。
- 修复：删除补丁文件与 conandata patches 条目，改为 conanfile
  _patch_current_user_fallback() 锚定文本替换（幂等，锚点缺失抛错），
  逻辑与原补丁一致（$USER/$LOGNAME/getlogin()/ohos 回退）。
