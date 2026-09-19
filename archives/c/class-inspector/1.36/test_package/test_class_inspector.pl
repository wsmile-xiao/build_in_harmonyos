#!/usr/bin/env perl
# test_class_inspector.pl — class-inspector 1.36 消费者真实 API 验证（R34）
#
# 由 test_class_inspector.py 以 perl -I<site> 调用，<site> 为 conan 打包目录中
# 含 Class/Inspector.pm 的 perl lib 根。断言语义按上游 t/ 实测确认：
#   t/class_inspector.t（方法接口，56 断言）、t/class_inspector_functions.t
#   （函数式接口，24 断言）、t/01_use.t（加载）、t/00_diag.t（环境诊断）
#
# ⚠️ 上游语义要点（实测确认，勿凭印象写）：
#   1. subclasses() 无命中时返回**空字符串 ''**、类名非法时返回 undef——
#      只在确有子类时才返回 ARRAY ref（实现：`@found ? \@found : ''`）。
#   2. 非法类名不要喂给 installed()/filename()：会触发 _inc_filename 对
#      undef 的取值；类名校验应使用 _class()（上游 t/class_inspector.t 即用它）。
use strict;
use warnings;

use File::Spec;
use Test::More;

use Class::Inspector ();

# Class::Inspector 自身可作被测对象（它是已加载且已安装的类）
use constant CI  => 'Class::Inspector';
use constant BAD => 'Class::Inspector::Nonexistant';

# 定义一个 Class::Inspector 的子类，用于 subclasses() 的命中场景
# （与上游 t/class_inspector.t 的 CLASS 段同思路）
BEGIN {
   package Class::Inspector::Dummy;
   use strict;
   require Class::Inspector;
   our @ISA = ('Class::Inspector');
   sub adummy1 { 1 }
}

package main;

# 1. 版本号与打包一致性
is( $Class::Inspector::VERSION, '1.36', 'Class::Inspector version is 1.36' );

# 2. 类是否已加载 / 是否安装
ok( CI->loaded(CI),        '->loaded detects a loaded class' );
ok( !CI->loaded(BAD),      '->loaded rejects a non-loaded class' );
ok( CI->installed(CI),     '->installed detects an installed class' );
ok( !CI->installed(BAD),   '->installed rejects a non-installed class' );

# 3. 文件名相关（filename 是 @INC 相对名，resolved_filename 走 @INC 解析）
{
   my $filename = CI->filename(CI);
   is( $filename, File::Spec->catfile('Class', 'Inspector.pm'),
       '->filename returns the @INC-relative module path' );

   ok( index( CI->loaded_filename(CI), $filename ) >= 0,
       '->loaded_filename points at the loaded file' );

   my $resolved = CI->resolved_filename(CI);
   ok( index( $resolved, $filename ) >= 0,
       '->resolved_filename resolves through @INC' );
   ok( -f $resolved, '->resolved_filename yields an existing file on disk' );
}

# 4. 函数枚举与存在性（上游 t/class_inspector.t 语义：包含私有 _class，引用为 CODE）
{
   my $functions = CI->functions(CI);
   ok( ref($functions) eq 'ARRAY', '->functions returns an ARRAY ref' );
   ok( (grep { $_ eq '_class' } @$functions) ? 1 : 0,
       '->functions includes the private _class helper' );

   my $refs = CI->function_refs(CI);
   ok( (ref($refs) eq 'ARRAY' and ref $refs->[0] eq 'CODE'),
       '->function_refs returns CODE refs' );

   ok( CI->function_exists( CI, 'installed' ),
       '->function_exists finds a known method' );
   ok( !CI->function_exists( CI, 'nsfladf' ),
       '->function_exists rejects an unknown name' );
   ok( !CI->function_exists( BAD, 'function' ),
       '->function_exists rejects an unknown class' );
}

# 5. 方法枚举（上游语义：公开方法数与私有方法数之和 = 函数总数）
{
   my $methods = CI->methods(CI);
   ok( ref($methods) eq 'ARRAY', '->methods returns an ARRAY ref' );
   ok( (grep { $_ eq 'installed' } @$methods) ? 1 : 0,
       '->methods includes a public method' );
}

# 6. 子类枚举（上游语义：命中→ARRAY ref；无命中→''；类名非法→undef）
{
   my $rv = CI->subclasses(CI);
   ok( (ref($rv) eq 'ARRAY' and (grep { $_ eq 'Class::Inspector::Dummy' } @$rv)),
       '->subclasses finds the defined subclass' );

   is( CI->subclasses(BAD), '',
       '->subclasses returns empty string when nothing matches' );
   is( CI->subclasses(''), undef,
       '->subclasses returns undef for an invalid class name' );
}

# 7. 类名校验（上游 _class 的校验契约；避免用非法名调 installed 触发 undef 警告）
{
   ok( CI->_class(CI),              '_class accepts a valid class' );
   ok( CI->_class(BAD),             '_class accepts a well-formed uninstalled class' );
   ok( CI->_class('A::B::C::D::E'), '_class accepts a long class name' );
   ok( !CI->_class(),               '_class rejects a missing class' );
   ok( !CI->_class('4teen'),        '_class rejects a digit-leading class' );
   ok( !CI->_class('Blah::%f'),     '_class rejects bad characters' );
}

# 8. 函数式接口（Class::Inspector::Functions 的 @EXPORT / @EXPORT_OK）
{
   require Class::Inspector::Functions;
   my $ok = 1;
   for my $f (qw( installed loaded filename functions methods subclasses
                  resolved_filename loaded_filename function_refs function_exists )) {
      $ok = 0 unless Class::Inspector::Functions->can($f);
   }
   ok( $ok, 'Class::Inspector::Functions provides all 10 exported functions' );

   Class::Inspector::Functions->import();
   ok( defined &installed && defined &loaded && defined &filename
       && defined &functions && defined &methods && defined &subclasses,
       'default-exported functions are importable' );
   ok( installed('Class::Inspector'), 'function-style installed() works' );
   ok( loaded('Class::Inspector'),    'function-style loaded() works' );
}

done_testing;
