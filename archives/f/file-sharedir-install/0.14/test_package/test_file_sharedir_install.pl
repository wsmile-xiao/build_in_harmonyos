#!/usr/bin/env perl
# test_file_sharedir_install.pl — file-sharedir-install 0.14 消费者真实 API 验证（R34）
#
# 本模块的用途是「让 Makefile.PL 声明并安装共享数据文件」，因此真实的消费者
# 验证 = 用打包后的模块**生成一个真实 Makefile 并执行 make**，检验共享文件是否
# 被装进 blib。思路与上游 t/10_makefile.t 一致，但使用自建临时夹具，不依赖
# 上游 t/ 下的数据，且全程在独立临时目录内进行（不污染 test_package）。
#
# 用法: test_file_sharedir_install.pl <site-perl-dir>
use strict;
use warnings;

use Config;
use Cwd qw( getcwd abs_path );
use File::Path qw( make_path rmtree );
use File::Spec;
use Test::More;
use ExtUtils::MakeMaker;

# File::ShareDir::Install 是普通 Exporter 模块（@EXPORT: install_share /
# delete_share），故必须用编译期 `use` 导入——运行期 import() 不能让解析器
# 认识裸字调用（会报 String found where operator expected）。
# ⚠️ 注意与 Test::* 系（Test::Builder::Module 子类）区别：后者 `use Foo qw(x)`
# 会把参数当 plan，需用 import => [...] 形式。
use File::ShareDir::Install;

my $site = shift or BAIL_OUT("usage: test_file_sharedir_install.pl <site-perl-dir>");
BAIL_OUT("site dir not found: $site") unless -d $site;

BAIL_OUT("install_share not imported")
    unless defined &install_share;

# 独立临时工作区（模块会在此生成 Makefile 与 blib）
my $work = File::Spec->catdir(File::Spec->tmpdir, "fsdi-consumer-$$");
rmtree([$work], 0, 0) if -d $work;
make_path($work) or BAIL_OUT("cannot create work dir $work");
my $orig = getcwd();
chdir $work or BAIL_OUT("cannot chdir to $work");
END {
    chdir $orig if $orig && -d $orig;
    rmtree([$work], 0, 0) if $work && -d $work;
}

my $share_dir = 'share';
my $mod_dir   = 'module';

# 准备临时共享数据：dist 级 + 模块级（含子目录、含空格文件名、含隐藏文件）
make_path($share_dir, "$mod_dir/deeper");
open my $fh, '>', "$share_dir/honk"        or BAIL_OUT($!); print $fh "bonk\n";   close $fh;
open $fh,    '>', "$share_dir/hello world" or BAIL_OUT($!); print $fh "hi\n";     close $fh;
open $fh,    '>', "$share_dir/.something"  or BAIL_OUT($!); print $fh "dot\n";    close $fh;
open $fh,    '>', "$mod_dir/bonk"          or BAIL_OUT($!); print $fh "bonk\n";   close $fh;
open $fh,    '>', "$mod_dir/deeper/bonk"   or BAIL_OUT($!); print $fh "deeper\n"; close $fh;

# 1. 模块版本与打包一致性
is( $File::ShareDir::Install::VERSION, '0.14',
    'File::ShareDir::Install version is 0.14' );

# 2. 导出接口齐全（@EXPORT: install_share/delete_share；@EXPORT_OK: postamble）
{
   my $ok = 1;
   for my $f (qw( install_share delete_share postamble )) {
      $ok = 0 unless File::ShareDir::Install->can($f);
   }
   ok( $ok, 'install_share / delete_share / postamble are all provided' );
}

# 3. 非法参数必须 confess（上游 install_share 的类型校验）
{
   my $died = eval { install_share 'bogus' => $share_dir; 1 } ? 0 : 1;
   ok( $died, 'install_share with invalid type must confess' );
}

# 4. 登记共享目录（真实消费者用法）
install_share 'dist' => $share_dir;
install_share module => 'My::Test' => $mod_dir;

# 5. 生成真实 Makefile；postamble 注入共享文件复制规则
my $mkfile = 'consumer-Makefile';
delete $ENV{PERL_MM_OPT};

# 生成的 Makefile 会声明对同目录 Makefile.PL 的依赖（`$mkfile: Makefile.PL`），
# 故工作目录内必须有一个 Makefile.PL，否则 `make` 直接报
# "No rule to make target 'Makefile.PL'"。此处放一个等价的最小脚本即可。
open my $mpl, '>', 'Makefile.PL' or BAIL_OUT($!);
print $mpl <<'MPL';
use strict;
use warnings;
use ExtUtils::MakeMaker;
WriteMakefile(NAME => 'File::ShareDir::Install', PREREQ_PM => {});
MPL
close $mpl;

package MY;
use File::ShareDir::Install qw(postamble);

package main;

ExtUtils::MakeMaker::WriteMakefile(
   NAME         => 'File::ShareDir::Install',
   VERSION_FROM => File::Spec->catfile($site, 'File', 'ShareDir', 'Install.pm'),
   INST_LIB     => 'lib',
   PREFIX       => 'root',
   MAKEFILE     => $mkfile,
   PREREQ_PM    => {},
);

ok( -f $mkfile, "generated $mkfile" );
my $content = do { local (@ARGV, $/) = ($mkfile); <> };

ok( $content =~ /\bshare\/dist\b/, 'per-dist share target present' );
ok( $content =~ /share\/module\/My-Test/, 'per-module share target present' );
ok( $content !~ /\.something/, 'dotfiles excluded by default (INCLUDE_DOTFILES=0)' );

# 6. 真正执行 make，检验共享文件被复制进 blib
{
   my $top = File::Spec->catdir('lib', 'auto', 'share');
   my $out = qx{$Config{make} -f $mkfile 2>&1};
   my $rc  = $? >> 8;

   ok( $rc == 0, "make -f $mkfile succeeds" ) or diag($out);
   ok( -f "$top/dist/File-ShareDir-Install/honk",
       'dist shared file copied into blib' );
   ok( -f "$top/dist/File-ShareDir-Install/hello world",
       'dist shared file with spaces copied into blib' );
   ok( !-f "$top/dist/File-ShareDir-Install/.something",
       'dotfile NOT copied (dotfiles excluded by default)' );
   ok( -f "$top/module/My-Test/bonk",
       'module shared file copied into blib' );
   ok( -f "$top/module/My-Test/deeper/bonk",
       'module shared file in subdir copied into blib' );
}

done_testing;
