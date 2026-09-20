#!/usr/bin/env perl
# test_future_queue.pl — future-queue 0.52 消费者真实 API 验证（R34）
#
# 以消费者视角载入**已打包**的 Future::Queue，真实调用其全部公开 API：
#   Future::Queue->new( max_items => N )
#   $q->push(@items)   → 返回 Future（受 max_items 背压时可为 pending）
#   $q->shift          → 返回 Future，队列空则 pending、push 后完成
#   $q->shift_atmost($n) → 批量版，返回多值
#   $q->finish         → 标记结束，之后 shift 产出空
# 并用 Future 的 await 驱动真实异步语义；含负例（finish 后 push 必须抛异常）。
use strict;
use warnings;

use Test::More;
# 不使用 `await`：Future 并未导出它（实测 `use Future qw(await)` 报
# "Attempt to call undefined import method with arguments"），上游 t/ 亦不使用 ——
# 上游惯用法是直接 `$future->result`（就绪时取值）与 `$future->is_done/is_ready`
# 判定状态，本文件全部照此写法。
use Future;
use Future::Queue;

# 1. 版本与模块可载入
is($Future::Queue::VERSION, '0.52', 'version is 0.52');
ok(Future::Queue->can('new'),          'new 可调用');
ok(Future::Queue->can('push'),         'push 可调用');
ok(Future::Queue->can('shift'),        'shift 可调用');
ok(Future::Queue->can('shift_atmost'), 'shift_atmost 可调用');
ok(Future::Queue->can('finish'),       'finish 可调用');

# 2. push 在 shift 之前：shift 立即就绪（上游 t/01queue.t 同款语义）
{
   my $q = Future::Queue->new;
   $q->push("ITEM");
   my $f = $q->shift;
   ok($f->is_done, 'push 先于 shift：shift 立即就绪');
   is($f->result, "ITEM", 'shift->result 取到该项');
}

# 3. shift 在 push 之前：pending → push 后完成（真实异步语义）
{
   my $q = Future::Queue->new;
   my $f = $q->shift;
   ok(!$f->is_done, 'shift 先于 push：尚未就绪');
   $q->push("ITEM");
   ok($f->is_done, 'push 后该 Future 完成');
   is($f->result, "ITEM", 'result 正确');
}

# 4. FIFO 顺序（多值 push；照上游 t/04bulk.t 用 ->result 直接取值）
{
   my $q = Future::Queue->new;
   $q->push("a", "b", "c");
   is($q->shift->result, "a", 'FIFO 第 1 项');
   is($q->shift->result, "b", 'FIFO 第 2 项');
   is($q->shift->result, "c", 'FIFO 第 3 项');
}

# 5. shift_atmost：批量取出（上游 t/04bulk.t 语义：返回多值 Future）
{
   my $q = Future::Queue->new;
   $q->push(1, 2, 3, 4);
   is_deeply([$q->shift_atmost(2)->result], [1, 2], 'shift_atmost(2) 取前两个');
   is_deeply([$q->shift_atmost(10)->result], [3, 4],
             'shift_atmost 可取剩余（不足 N 时全取）');
   ok(!$q->shift_atmost(2)->is_ready, '队列空时 shift_atmost 返回 pending');
}

# 6. max_items 背压：队列满时 push 返回 pending 的 Future
{
   my $q = Future::Queue->new(max_items => 1);
   my $p1 = $q->push("first");
   ok($p1->is_done, 'max_items=1：首项 push 立即完成');
   my $p2 = $q->push("second");
   ok(!$p2->is_done, 'max_items=1：第二项 push 受背压，Future 仍 pending');
   is($q->shift->result, "first", '取出首项');
   ok($p2->is_done, 'shift 腾出空间后，被压的 push 完成');
   is($q->shift->result, "second", '被压入的项正确取回');
}

# 7. finish：耗尽后 shift 产出空列表
{
   my $q = Future::Queue->new;
   $q->push("only");
   $q->finish;
   is($q->shift->result, "only", 'finish 后已入队项仍可取');
   is_deeply([$q->shift->result], [], 'finish 且耗尽后 shift 产出空列表');
}

# 8. 负例：finish 之后再 push 必须抛异常（证明非恒真空壳）
{
   my $q = Future::Queue->new;
   $q->finish;
   my $err = "";
   eval { $q->push("nope"); 1 } or $err = $@;
   like($err, qr/[Cc]annot.*push.*finished/, '负例：finish 后 push 抛异常');
}

# 9. 负例：pending 的 shift Future 在 push 之前不应 ready
{
   my $q = Future::Queue->new;
   my $f = $q->shift;
   ok(!$f->is_ready, '负例：无数据时 shift 的 Future 不 ready');
   ok(!$f->is_done,  '负例：无数据时 shift 的 Future 未完成');
}

done_testing;
print "\nALL OK - future-queue 0.52 consumer checks passed\n";
