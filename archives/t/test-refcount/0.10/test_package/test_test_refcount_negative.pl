#!/usr/bin/env perl
# test_test_refcount_negative.pl — test-refcount 0.10 失败路径验证
#
# 验证 is_refcount / is_oneref 在「非引用入参」与「引用数不符」两条失败路径上的
# **真实行为与诊断文案**。本脚本故意让被测断言失败（因此进程退出码非 0），由
# test_test_refcount.py 核对 STDOUT 的 TAP 中确实出现预期诊断。
#
# 采用这种「观察真实 TAP」的方式而非上游的 Test::Builder::Tester：后者要求用
# test_fail(N) 给出与行号强耦合的 offset，测试文件与上游不同行时会误报失配，
# 直接观察 TAP 更稳健，且同样不伪造结论。
use strict;
use warnings;

use Test::More;
use Scalar::Util qw( weaken );

use Test::Refcount;

# 1. 非引用入参 → 断言失败 + "expected a reference, was not given one"
is_refcount( "hello", 1, 'not ref' );

# 2. 引用数不符（期望 1，实际 2）→ 断言失败 + "expected 1 references, found 2"
my $object = bless {}, 'Some::Class';
my $extra  = $object;
is_refcount( $object, 1, 'one ref' );

# 3. is_oneref 同样报出实际引用数
is_oneref( $object, 'one ref via is_oneref' );

# 4. weak 引用**不计入**引用数，但此处 $extra 仍是**强引用**（未 undef），
#    故实际引用数为 2，is_oneref 按预期失败并报出实际值。
#    若要正向对照「weak 不计入」，须先 undef $extra（见正向脚本的对应断言）。
is_oneref( $object, 'weak ref not counted' );

done_testing;
