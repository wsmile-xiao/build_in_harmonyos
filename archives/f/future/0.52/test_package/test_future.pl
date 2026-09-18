#!/usr/bin/env perl
# test_future.pl — future 0.52 消费者真实 API 验证（R34）
#
# 由 test_future.py 以 perl -I<site> 调用，<site> 为 conan 打包目录中
# 含 Future.pm 的 perl lib 根。逐项断言，全部通过后打印 ALL OK。
use strict;
use warnings;

use Future;
use Future::Utils qw(call fmap_void repeat);
use Future::Mutex;

my $failures = 0;
sub check {
   my ($name, $cond) = @_;
   if ($cond) {
      print "ok - $name\n";
   } else {
      print "not ok - $name\n";
      $failures++;
   }
}

# 1. 版本号与打包一致性
check("Future version is 0.52", Future->VERSION eq '0.52');

# 2. 立即完成的 future：done + get
my $immediate = Future->done("hello");
check("done() future is ready", $immediate->is_ready);
check("get() returns the result", $immediate->get eq "hello");

# 3. 链式 then（异步序列）
my $chained = Future->done(2)
   ->then(sub { my $v = shift; return Future->done($v * 21) });
check("then() chains a result", $chained->get == 42);

# 4. 失败传播：fail + failure
my $bad = Future->fail("expected error");
check("fail() future carries the failure", $bad->failure eq "expected error");

# 5. 组合器 wait_all —— 结果是各子 future 本身（非其返回值）
my $wa = Future->wait_all(Future->done("a"), Future->done("b"));
my @wa_res = $wa->result;
check("wait_all() is ready once all subs are ready", $wa->is_ready);
check("wait_all() result lists both sub-futures", scalar @wa_res == 2);

# 6. 组合器 needs_all —— 结果是各子 future 的返回值
my @na_res = Future->needs_all(Future->done(1), Future->done(2))->result;
check("needs_all() collects sub-results", join(",", @na_res) eq "1,2");

# 7. Future::Utils::call —— 返回 code 块返回的 future
my $called = call { return Future->done("from-call") };
check("Future::Utils::call() returns the inner future", $called->get eq "from-call");

# 8. Future::Utils::call —— die 转为立即失败（上游语义）
my $died = call { die "boom\n" };
check("call() turns die() into immediate failure", $died->failure eq "boom\n");

# 9. Future::Utils::fmap_void —— 对每个输入项执行一次，结果为空
my @seen;
my $mapped = fmap_void(
   sub { my ($item) = @_; push @seen, $item; return Future->done },
   foreach => [1, 2, 3],
);
$mapped->get;
check("fmap_void() iterates all items", join(",", sort @seen) eq "1,2,3");
my @mapped_res = $mapped->result;
check("fmap_void() result list is empty", scalar @mapped_res == 0);

# 10. Future::Utils::repeat —— 按 while 条件重复
my $count = 0;
my $repeated = repeat(
   sub { $count++; return Future->done($count) },
   while => sub { $count < 3 },
);
$repeated->get;
check("repeat() runs the expected number of trials", $count == 3);

# 11. Future::Mutex —— 串行化临界区（enter 的 code 须返回 future）
my $mutex = Future::Mutex->new;
check("Mutex is available when unlocked", $mutex->available);
my @order;
my $m1 = $mutex->enter(sub { push @order, "first"; return Future->done });
my $m2 = $mutex->enter(sub { push @order, "second"; return Future->done });
$m1->get;
$m2->get;
check("Mutex serialises critical sections", join(",", @order) eq "first,second");

# 12. Future::Exception 随包安装且可加载
eval { require Future::Exception; 1 };
check("Future::Exception is packaged and loadable", !$@);

if ($failures) {
   print "\nFAILED: $failures check(s)\n";
   exit 1;
}
print "\nALL OK\n";
exit 0;
