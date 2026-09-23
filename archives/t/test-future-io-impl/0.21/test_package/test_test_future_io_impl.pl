#!/usr/bin/env perl
# test_test_future_io_impl.pl — test-future-io-impl 0.21 消费者真实 API 验证（R34）
#
# 本模块的用途是「给 Future::IO 实现方提供验收测试套件」，其 API 只有
# `run_tests @suitenames`（外加内部计时助手 time_about）。因此真实的消费者验证
# 应当是：提供一份 **Future::IO 桩实现**，让 run_tests 真正驱动一个验收套件并
# 断言其行为 —— 而不是只做「模块能加载」。
#
# 这里选 `sleep` 套件：它自包含（不需要 socket/pipe/fork），最能稳定地在
# 容器/CI 环境复现。桩实现按 Future::IO 的契约提供 sleep/alarm，并返回带
# get/cancel/await/is_ready 的 future 对象。
#
# 说明：完整的 13 个验收套件需要真实的 Future::IO 及其实现（OHOS 环境与
# ohpcd 制品仓均无 Future::IO，本仓亦尚无相应归档），故此处只实跑 sleep 套件，
# 并对「其余 12 个套件均已随包安装」做存在性核验。这是如实申报的覆盖边界。
#
# 用法: test_test_future_io_impl.pl <site-perl-dir>
use strict;
use warnings;

use Test2::V0;
use Time::HiRes qw( sleep time );

my $site = shift or BAIL_OUT("usage: test_test_future_io_impl.pl <site-perl-dir>");
BAIL_OUT("site dir not found: $site") unless -d $site;

use Test::Future::IO::Impl;

# ── Future::IO 桩实现（仅供验收套件调用；不冒充真实实现）────────────────
package Future::IO;

# sleep($sec) → 计时未来；alarm($abs_time) → 到点未来
# 注意用 ->new（方法调用）传入类名：写成 ::new($dur) 会把时长当成类名。
sub sleep { return Future::IO::_Stub->new( $_[1] ) }
sub alarm { return Future::IO::_Stub->new( $_[1] - Time::HiRes::time() ) }

package Future::IO::_Stub;

sub new {
   my ($class, $dur) = @_;
   $dur = 0 if !defined $dur || $dur < 0;
   return bless { dur => $dur, start => Time::HiRes::time(),
                  cancelled => 0 }, $class;
}

# 计时未来在时长耗尽（或被取消）后就绪
sub is_ready {
   my $self = shift;
   return 1 if $self->{cancelled};
   return ( Time::HiRes::time() - $self->{start} >= $self->{dur} ) ? 1 : 0;
}

sub cancel { my $self = shift; $self->{cancelled} = 1; return $self }

sub await {
   my $self = shift;
   my $left = $self->{dur} - ( Time::HiRes::time() - $self->{start} );
   Time::HiRes::sleep($left) if !$self->{cancelled} && $left > 0;
   return $self;
}

sub get {
   my $self = shift;
   $self->await;
   return undef;
}

package main;

# ── 断言 ─────────────────────────────────────────────────────────────

# 1. 版本与打包一致性
is( $Test::Future::IO::Impl::VERSION, '0.21',
    'Test::Future::IO::Impl version is 0.21' );

# 2. run_tests 已导出（@EXPORT）
ok( defined &run_tests, 'run_tests is exported by default' );

# 3. 全部 13 个验收套件方法随包安装（can → 存在性核验）
{
   my @suites = qw( accept connect poll_no_hup poll read sysread recv recvfrom
                    send sleep write syswrite waitpid );
   my @missing = grep { !Test::Future::IO::Impl->can("run_${_}_test") } @suites;
   is( \@missing, [], 'all 13 acceptance suites are provided' )
      or diag("missing: @missing");
}

# 4. time_about 计时助手存在（各套件依赖它）
ok( Test::Future::IO::Impl->can('time_about'),
    'time_about timing helper is provided' );

# 5. 未知套件名必须 die（run_tests 的分发契约）
{
   my $died = eval { run_tests 'no_such_suite_name'; 1 } ? 0 : 1;
   ok( $died, 'run_tests dies on an unrecognised suite name' );
}

# 6. 真实驱动一个验收套件：sleep（含 sleep/取消/await/alarm 共 6 项断言，
#    由模块自身通过 Test2 上下文报出）
run_tests 'sleep';

done_testing;
