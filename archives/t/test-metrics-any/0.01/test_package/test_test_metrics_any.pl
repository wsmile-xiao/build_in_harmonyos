#!/usr/bin/env perl
# test_test_metrics_any.pl — test-metrics-any 0.01 消费者真实 API 验证（R34）
#
# 以消费者视角载入**已打包**的 Test::Metrics::Any，真实调用其导出 API：
#   is_metrics( \%expect, $name )                 —— 断言指标当前值
#   is_metrics_from( sub {...}, \%expect, $name ) —— 断言代码块产生的指标
#   谓词助手 positive / at_least / greater_than
# 并含**负例**（值不匹配 / 指标缺失），证明断言真的会失败而非恒真。
#
# 写法遵循上游 t/01metrics.t 的惯用法：由于 is_metrics 经 Test::Builder 直接
# 输出 TAP，必须用 Test::Builder::Tester 的 test_out/test_test 包裹每次调用，
# 否则其 TAP 会与本文件自身的 Test::More 断言流混在一起、计数错乱。
use strict;
use warnings;

use Test::More;
use Test::Builder::Tester;
use Test::Metrics::Any;
use Metrics::Any '$metrics';
use Metrics::Any::Adapter::Test;

# 1. 版本号与打包一致性
is($Test::Metrics::Any::VERSION, '0.01', 'Test::Metrics::Any version is 0.01');

# 2. 导出函数确实存在（上游 @EXPORT: is_metrics / is_metrics_from）
ok(defined &is_metrics, 'is_metrics 已导出');
ok(defined &is_metrics_from, 'is_metrics_from 已导出');

# 3. 谓词助手返回可用对象（注意：谓词**不在 @EXPORT 中**，上游 t/02predicates.t
#    亦以全限定名 Test::Metrics::Any::positive 调用，故此处必须全限定）
ok(Test::Metrics::Any::positive(),      '谓词 positive 可用');
ok(Test::Metrics::Any::at_least(3),     '谓词 at_least 可用');
ok(Test::Metrics::Any::greater_than(2), '谓词 greater_than 可用');

# 4. is_metrics：精确值断言（正例）
{
   Metrics::Any::Adapter::Test->clear;
   $metrics->make_counter('basic' => name => "a_basic_metric");
   $metrics->inc_counter('basic') for 1 .. 3;

   test_out("ok 1 - basic exact");
   is_metrics({ a_basic_metric => 3 }, "basic exact");
   test_test("is_metrics 精确值断言通过");
}

# 5. is_metrics：带标签指标的命名格式 "name label:value"（正例）
{
   Metrics::Any::Adapter::Test->clear;
   $metrics->make_counter('labelled' => name => "a_labelled_metric",
                                       labels => [qw( label )]);
   $metrics->inc_counter('labelled' => [ label => "here" ]);

   test_out("ok 1 - labelled");
   is_metrics({ "a_labelled_metric label:here" => 1 }, "labelled");
   test_test("is_metrics 支持标签指标（name label:value 命名）");
}

# 6. is_metrics：谓词断言（正例；上游 PREDICATES 文档语义）
{
   Metrics::Any::Adapter::Test->clear;
   $metrics->make_counter('pred' => name => "a_pred_metric");
   $metrics->inc_counter('pred') for 1 .. 7;

   test_out("ok 1 - at_least ok");
   is_metrics({ a_pred_metric => Test::Metrics::Any::at_least(5) }, "at_least ok");
   test_test("谓词 at_least(5) 对值 7 成立");

   test_out("ok 1 - greater ok");
   is_metrics({ a_pred_metric => Test::Metrics::Any::greater_than(6) }, "greater ok");
   test_test("谓词 greater_than(6) 对值 7 成立");

   test_out("ok 1 - positive ok");
   is_metrics({ a_pred_metric => Test::Metrics::Any::positive() }, "positive ok");
   test_test("谓词 positive 对值 7 成立");
}

# 7. is_metrics_from：断言代码块产生的指标（正例）
{
   Metrics::Any::Adapter::Test->clear;
   $metrics->make_counter('from' => name => "a_from_metric");

   test_out("ok 1 - from ok");
   is_metrics_from(
      sub { $metrics->inc_counter('from') for 1 .. 4 },
      { a_from_metric => 4 },
      "from ok",
   );
   test_test("is_metrics_from 断言代码块产生的指标");
}

# 8. 文档语义：被测代码上报了**额外**指标不应失败（正例）
{
   Metrics::Any::Adapter::Test->clear;
   $metrics->make_counter('only'  => name => "a_only_metric");
   $metrics->make_counter('extra' => name => "a_extra_metric");
   $metrics->inc_counter('only');
   $metrics->inc_counter('extra');

   test_out("ok 1 - subset ok");
   is_metrics({ a_only_metric => 1 }, "subset ok");
   test_test("仅校验哈希中提到的指标（额外指标不导致失败）");
}

# 9. 负例 A：值不匹配 → 断言必须失败
#
# ⚠️ 负例只断言 **stdout**（test_out 必须出现 "not ok"），并用
# `skip_err => 1` 跳过 stderr 比对。原因：Test::Builder::Tester 的
# `test_fail`/`test_err` 把 Test::Builder 的「Failed test ... at line N」诊断
# 按**调用点行号**锚定，对本文件的任何增删行（含注释）都会误报——实测反复踩到
# （期望 line 119、实际 119 仍失配，因期望列表只覆盖前两行而实际有三行）。
# 非空壳性由 test_out 充分保证：若 is_metrics 是空壳（不报错或报 ok），
# 这里必然拿不到 "not ok 1 - should fail" 而失败。
{
   Metrics::Any::Adapter::Test->clear;
   $metrics->make_counter('neg' => name => "a_neg_metric");
   $metrics->inc_counter('neg');

   test_out("not ok 1 - should fail");
   is_metrics({ a_neg_metric => 999 }, "should fail");
   test_test(name => "负例：值不匹配时 is_metrics 确实失败（非恒真）", skip_err => 1);
}

# 10. 负例 B：指标缺失 → 断言必须失败
{
   Metrics::Any::Adapter::Test->clear;

   test_out("not ok 1 - should fail");
   is_metrics({ a_missing_metric => 1 }, "should fail");
   test_test(name => "负例：指标缺失时 is_metrics 确实失败（非恒真）", skip_err => 1);
}

# 末尾按真实结果打印标记：**必须**在 done_testing() 之前取 is_passing，
# 否则失败时仍打印 "ALL OK" 会骗过驱动脚本的标记检查（空壳通过的另一种形态）。
my $passing = Test::More->builder->is_passing;
done_testing;
if ($passing) {
   print "\nALL OK - test-metrics-any 0.01 consumer checks passed\n";
} else {
   print "\nFAILED - test-metrics-any 0.01 consumer checks\n";
   exit 1;
}
