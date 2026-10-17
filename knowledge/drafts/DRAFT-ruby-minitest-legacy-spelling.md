# 上游 Ruby minitest 套件旧拼写 `MiniTest::Test` 在设备 minitest 5.25.4 下加载即 NameError

> Draft: DRAFT-OHOS-RUBY-MINITEST-LEGACY-SPELLING-NAMEERROR
> Stem: `ruby-minitest-legacy-spelling` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-OHOS-RUBY-MINITEST-LEGACY-SPELLING-NAMEERROR
- **严重度**: 2
- **类别**: dependency-closure-testsuite（依赖闭包/测试套件）
- **触发工具**: ruby 3.4.5（内置 minitest 5.25.4）| rake 13.2.1 | make check

## 错误特征

```
test/test_bom_detection.rb:3:in '<top (required)>': uninitialized constant MiniTest (NameError)

class BOMDetectionTest < MiniTest::Test
                         ^^^^^^^^
Did you mean?  Minitest
rake aborted!
Command failed with status (1)
make: *** [Makefile:15: check] Error 1
```

## 真实失败证据（本 run 实录）

detenc 2.0.0 上游 `make check`（`cd test && rake test`）在设备上未打补丁时
一个用例都没跑即中止：`uninitialized constant MiniTest (NameError)`，
7 个 `test_*.rb` 全部使用旧拼写。最小复现（注意裸 `ruby -e` 不自动加载
minitest，必须先 require）：

```bash
ruby -e 'require "minitest/autorun"; p MiniTest::Test'
# => -e:1:in '<main>': uninitialized constant MiniTest (NameError)
ruby -e 'require "minitest/autorun"; p Minitest::Test'
# => Minitest::Test
```

## 根因

上游测试写于 minitest 1.x~4.x 时代，依赖旧 camel-case 常量 `MiniTest`；
minitest 5.x 起该兼容别名被移除。设备 ruby 3.4.5 内置 minitest 5.25.4，
命中缺口。Alpine 对同一问题早有同名 minitest.patch 处理，可直接借鉴。

## 推荐方案（rec_priority 1）

最小大小写修正补丁（不改任何测试语义）：

```bash
for f in test/test_*.rb; do sed -i 's/MiniTest::Test/Minitest::Test/' $f; done
# 用 diff -u --label a/<path> --label b/<path> 生成 0001-*.patch 入库，
# 记入 conandata.yml（含补丁 sha256），先在干净树上 patch -p1 复验，再跑全量 make check
```

detenc 2.0.0 修复后实测全量：**43 runs, 334 assertions, 0 failures, 0 errors,
0 skips**。

## 附带说明（非硬失败）

Tempfile 类测试依赖 TMPDIR：设备登录 shell 已设 `TMPDIR=/storage/Users/currentUser/tmp`
（可写）；即使 unset，Ruby 3.4 在 /tmp 只读（E002）时也会回退 $HOME 并打
`system temporary path is not writable: /tmp` 告警，不致硬失败。建议在构建命令
显式 `TMPDIR=<构建目录>` 保持测试运行自包含、避免 $HOME 污染。

## 禁止事项

- 禁止以修改测试断言、删除/跳过旧拼写测试文件的方式绕过 NameError——
  大小写修正不改语义，是最小可解释补丁；删改测试会伪造上游测试结论。
