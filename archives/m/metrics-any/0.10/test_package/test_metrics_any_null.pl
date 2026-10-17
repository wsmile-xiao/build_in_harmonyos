#!/usr/bin/env perl
# test_metrics_any_null.pl — metrics-any 0.10 Null 适配器验证（独立进程）
#
# ⚠️ 必须独立进程运行：Metrics::Any 的适配器一旦确定就不能在同一进程内更换
# （上游 t/10adapter-null.t 也是独立 .t 文件）。在已设定 Test 适配器的进程里
# `use Metrics::Any::Adapter 'Null'` 不会生效，$metrics 仍为真。
use strict;
use warnings;

use Metrics::Any '$metrics';
use Metrics::Any::Adapter 'Null';

my $failures = 0;
sub check {
   my ($name, $cond) = @_;
   if ($cond) { print "ok - $name\n" } else { print "not ok - $name\n"; $failures++ }
}

check('$metrics is defined', defined $metrics);
check('$metrics appears true before adapter', $metrics ? 1 : 0);

$metrics->adapter;   # force 创建适配器

check('$metrics appears false with Null adapter', $metrics ? 0 : 1);

# Null 适配器下全部上报 API 必须可用且静默
my @apis = (
   [ make_counter        => [ nc => ] ],
   [ inc_counter         => [ 'nc' ] ],
   [ inc_counter_by      => [ 'nc', 3 ] ],
   [ make_distribution   => [ nd => ] ],
   [ report_distribution => [ nd => 20 ] ],
   [ make_gauge          => [ ng => ] ],
   [ inc_gauge           => [ 'ng' ] ],
   [ inc_gauge_by        => [ ng => 20 ] ],
   [ set_gauge_to        => [ ng => 50 ] ],
   [ make_timer          => [ nt => ] ],
   [ report_timer        => [ nt => 20 ] ],
);
my $all_ok = 1;
for my $a (@apis) {
   my ($m, $args) = @$a;
   $all_ok = 0 unless eval { $metrics->$m( @$args ); 1 };
}
check('Null adapter 下全部上报 API 可用且静默', $all_ok);
check('Null adapter 支持批量模式回调', $metrics->add_batch_mode_callback( sub {} ) ? 1 : 0);
check('$metrics is still false at EOF', $metrics ? 0 : 1);

if ($failures) { print "\nFAILED: $failures check(s)\n"; exit 1 }
print "\nALL OK\n";
exit 0;
