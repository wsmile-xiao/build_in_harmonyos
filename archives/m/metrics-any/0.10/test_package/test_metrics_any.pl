#!/usr/bin/env perl
# test_metrics_any.pl — metrics-any 0.10 消费者真实 API 验证（R34）
#
# 由 test_metrics_any.py 以 perl -I<site> 调用，<site> 为 conan 打包目录中
# 含 Metrics/Any.pm 的 perl lib 根。断言语义按上游 t/ 实测确认：
#   t/01collector.t、t/10adapter-null.t、t/13adapter-stored.t、t/14adapter-test.t
use strict;
use warnings;

use Metrics::Any '$metrics', strict => 1;
use Metrics::Any::Adapter 'Test';

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
check("Metrics::Any version is 0.10", Metrics::Any->VERSION eq '0.10');

# 2. $metrics 全局对象被 import 且为真（adapter 尚未创建时）
check('$metrics is defined', defined $metrics);
check('$metrics appears true before adapter', $metrics ? 1 : 0);

# Force the adapter to exist
$metrics->adapter;

# 3. Test 适配器：无标签 counter
{
   Metrics::Any::Adapter::Test->clear;

   $metrics->make_counter( abc => name => "the_ABC_counter" );
   $metrics->make_counter( def => name => [qw( the DEF counter )] );

   $metrics->inc_counter( 'abc' );
   $metrics->inc_counter( 'def' );
   $metrics->inc_counter( 'def' );
   $metrics->inc_counter( 'def' );

   check("counter 上报与聚合（1 / 3）",
      Metrics::Any::Adapter::Test->metrics eq
         "the_ABC_counter = 1\n" . "the_DEF_counter = 3\n");
}

# 4. Test 适配器：带标签 counter（ARRAYref 与 HASHref 两种传参）
{
   Metrics::Any::Adapter::Test->clear;

   $metrics->make_counter( ghi => name => "the_GHI_counter",
                                  labels => [qw( label )] );
   $metrics->make_counter( jkl => name => "the_JKL_counter",
                                  labels => [qw( x y )] );

   $metrics->inc_counter( ghi => [ label => "value" ] );
   $metrics->inc_counter( jkl => [ x => 10, y => 20 ] );
   check("counter 带标签（ARRAYref）",
      Metrics::Any::Adapter::Test->metrics eq
         "the_GHI_counter label:value = 1\n" . "the_JKL_counter x:10 y:20 = 1\n");

   $metrics->inc_counter( ghi => { label => "value" } );
   $metrics->inc_counter( jkl => { x => 10, y => 20 } );
   check("counter 带标签（HASHref）",
      Metrics::Any::Adapter::Test->metrics eq
         "the_GHI_counter label:value = 2\n" . "the_JKL_counter x:10 y:20 = 2\n");
}

# 5. gauge：inc_gauge / inc_gauge_by / set_gauge_to
{
   Metrics::Any::Adapter::Test->clear;

   $metrics->make_gauge( g => name => "the_G_gauge" );
   $metrics->inc_gauge( 'g' );
   check("gauge inc_gauge", Metrics::Any::Adapter::Test->metrics eq "the_G_gauge = 1\n");

   $metrics->inc_gauge_by( g => 2 );
   check("gauge inc_gauge_by 累加", Metrics::Any::Adapter::Test->metrics eq "the_G_gauge = 3\n");

   $metrics->set_gauge_to( g => 50 );
   check("gauge set_gauge_to 覆盖", Metrics::Any::Adapter::Test->metrics eq "the_G_gauge = 50\n");
}

# 6. distribution：report_distribution
{
   Metrics::Any::Adapter::Test->clear;

   $metrics->make_distribution( d => name => "the_D_dist" );
   $metrics->report_distribution( d => 5 );
   check("distribution 首次上报（count/total）",
      Metrics::Any::Adapter::Test->metrics eq
         "the_D_dist_count = 1\nthe_D_dist_total = 5\n");

   $metrics->report_distribution( d => 3 );
   check("distribution 累计（count=2 / total=8）",
      Metrics::Any::Adapter::Test->metrics eq
         "the_D_dist_count = 2\nthe_D_dist_total = 8\n");
}

# 7. timer：report_timer
{
   Metrics::Any::Adapter::Test->clear;

   $metrics->make_timer( t => name => "the_T_timer" );
   $metrics->report_timer( t => 0.02 );
   check("timer 首次上报",
      Metrics::Any::Adapter::Test->metrics eq
         "the_T_timer_count = 1\nthe_T_timer_total = 0.02\n");
}

# 8. strict 模式：重复注册与未注册指标必须 die（上游 t/01collector.t 语义）
{
   my $ok = eval { $metrics->make_counter( dup => ); 1 };
   check("首次注册 counter 成功", $ok ? 1 : 0);

   my $died = eval { $metrics->make_counter( dup => ); 1 } ? 0 : 1;
   check("strict: 重复注册同一 counter 必须失败", $died);

   my $died2 = eval { $metrics->inc_counter( unregistered_xyz => ); 1 } ? 0 : 1;
   check("strict: 上报未注册 counter 必须失败", $died2);
}

# 9. AdapterBase::Stored 子类化（上游 t/13adapter-stored.t 的自定义适配器模式）
{
   my $loaded = eval { require Metrics::Any::AdapterBase::Stored; 1 };
   check("AdapterBase::Stored 随包安装", $loaded ? 1 : 0);
}

# 10. Adapter 基类与 Collector 随包安装
{
   my $ok = 1;
   for my $m (qw(Metrics::Any::Adapter Metrics::Any::Collector
                 Metrics::Any::Adapter::File Metrics::Any::Adapter::Stderr
                 Metrics::Any::Adapter::Tee Metrics::Any::Adapter::Test
                 Metrics::Any::Adapter::Null)) {
      my $p = $m; $p =~ s{::}{/}g; $p .= ".pm";
      $ok = 0 unless eval { require $p; 1 };
   }
   check("全部子模块随包安装且可加载", $ok);
}

# 11. 标量上下文下 $metrics 为真（Test 适配器已激活）
{
   check('$metrics is true with Test adapter', $metrics ? 1 : 0);
}

if ($failures) {
   print "\nFAILED: $failures check(s)\n";
   exit 1;
}
print "\nALL OK\n";
exit 0;
