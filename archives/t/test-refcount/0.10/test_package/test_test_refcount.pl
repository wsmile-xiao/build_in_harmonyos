#!/usr/bin/env perl
# test_test_refcount.pl — test-refcount 0.10 消费者真实 API 验证（R34）
#
# 由 test_test_refcount.py 以 perl -I<site> 调用，<site> 为 conan 打包目录中
# 含 Test/Refcount.pm 的 perl lib 根。断言语义按上游 t/ 实测确认：
#   t/01count.t（is_refcount）、t/02one.t（is_oneref）、t/03weak.t（weak ref
#   不计入引用数）、t/04reftypes.t（各引用类型）
use strict;
use warnings;

use Test::More;
use Scalar::Util qw( weaken );
use Symbol qw( gensym );
# Test::Refcount 继承 Test::Builder::Module，import 的参数会被当成 plan 参数；
# 取 @EXPORT_OK 里的 refcount 必须用上游 POD 的 `import => [...]` 形式。
use Test::Refcount import => [qw( is_refcount is_oneref refcount )];

# 1. 版本号与打包一致性
is( Test::Refcount->VERSION, '0.10', 'Test::Refcount version is 0.10' );

# 2. 匿名 ARRAY 引用：is_oneref / is_refcount 一致
{
   my $anon = [];
   is_oneref( $anon, 'anon ARRAY ref has 1 reference' );
   is_refcount( $anon, 1, 'anon ARRAY ref refcount == 1' );
}

# 3. 对象：别名使引用数上升，undef 后回落
{
   my $object = bless {}, 'Some::Class';
   is_oneref( $object, 'object has 1 reference after construct' );

   my $newref = $object;
   is_refcount( $object, 2, 'object has 2 references after aliasing' );

   undef $newref;
   is_oneref( $object, 'object back to 1 reference after undef' );
}

# 4. refcount() 公开 API（0.09+）：返回引用数
{
   my $object = bless {}, 'Some::Class';
   ok( refcount($object) == 1, 'refcount() returns 1 for a fresh object' );
}

# 5. weak 引用不计入引用数（上游 t/03weak.t 语义）
{
   my $object = bless {}, 'Some::Class';
   my $weakref = $object;
   weaken($weakref);
   is_oneref( $object, 'weak reference does not count toward refcount' );
}

# 6. 循环自引用被计入（上游 t/01count.t 语义）
{
   my $object = bless {}, 'Some::Class';
   $object->{self} = $object;
   is_refcount( $object, 2, 'circular self-reference counts as 2' );
   delete $object->{self};
   is_oneref( $object, 'back to 1 after removing the cycle' );
}

# 7. 各引用类型均可判定（上游 t/04reftypes.t 语义）
#    按上游写法构造匿名引用：SCALAR 用 `do { my $var; \$var }` 让词法槽位
#    及时出作用域，否则该标量被槽位与引用同时持有、refcount 为 2（实测）。
#    正则引用在现代 perl 起始 refcount 为 2，上游对该类型显式 skip（"Bleadperl"，
#    perl >= 5.011），故此处同样不纳入。
{
   my $scalarref = do { my $var; \$var };
   my $arrayref  = [];
   my $hashref   = {};
   my $coderef   = do { my $inner; sub { $inner } };
   my $globref   = gensym();

   my $all_ok = 1;
   $all_ok &&= refcount($scalarref) == 1;
   $all_ok &&= refcount($arrayref)  == 1;
   $all_ok &&= refcount($hashref)   == 1;
   $all_ok &&= refcount($coderef)   == 1;
   $all_ok &&= refcount($globref)   == 1;
   ok( $all_ok, 'SCALAR/ARRAY/HASH/CODE/GLOB refs each report refcount 1' );
}

# 8. 导出接口齐全（@EXPORT: is_refcount/is_oneref；@EXPORT_OK: refcount）
{
   my $ok = 1;
   for my $f (qw( is_refcount is_oneref refcount )) {
      $ok = 0 unless Test::Refcount->can($f);
   }
   ok( $ok, 'is_refcount / is_oneref / refcount are all provided' );
}

done_testing;
