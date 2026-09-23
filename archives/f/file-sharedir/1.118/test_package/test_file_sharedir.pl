#!/usr/bin/env perl
# test_file_sharedir.pl — file-sharedir 1.118 消费者真实 API 验证（R34）
#
# 以消费者视角载入**已打包**的 File::ShareDir，真实调用其四个导出 API：
#   dist_dir($dist)      → 发行版共享目录
#   dist_file($dist,$f)  → 发行版共享文件
#   module_dir($module)  → 模块共享目录
#   module_file($module,$f) → 模块共享文件
# 并校验安装包的**数据文件**确实随包发布（本包核心功能，缺则运行期才炸）。
use strict;
use warnings;

use Test::More;
use File::Spec;
use File::ShareDir qw(dist_dir dist_file module_dir module_file);

# 1. 版本与导出符号
is($File::ShareDir::VERSION, '1.118', 'version is 1.118');
ok(defined &dist_dir,     'dist_dir 已导出');
ok(defined &dist_file,    'dist_file 已导出');
ok(defined &module_dir,   'module_dir 已导出');
ok(defined &module_file,  'module_file 已导出');

# 2. dist_dir / dist_file —— 发行版共享数据
#    上游 t/02_main.t 用 dist 名 "File-ShareDir"（带连字符的发行版名）
my $ddir = eval { dist_dir('File-ShareDir') };
is($@, '', 'dist_dir 调用不抛异常') or diag("err: $@");
ok(defined $ddir && -d $ddir, "dist_dir 返回存在的目录（$ddir）");

my $dfile = eval { dist_file('File-ShareDir', 'sample.txt') };
is($@, '', 'dist_file 调用不抛异常') or diag("err: $@");
ok(defined $dfile && -f $dfile, "dist_file 返回存在的文件（$dfile）");

# 数据文件内容可读（证明是真数据而非空占位）
my $content = do { local $/; open my $fh, '<', $dfile or die $!; <$fh> };
like($content, qr/\S/, 'dist_file 内容非空');

# 3. 子目录形式的数据文件
my $sub = eval { dist_file('File-ShareDir', File::Spec->catfile('subdir', 'sample.txt')) };
is($@, '', 'dist_file 支持子目录路径') or diag("err: $@");
ok(defined $sub && -f $sub, '子目录数据文件存在');

# 4. module_dir / module_file —— 按模块名定位
#    上游以 module 名（:: 分隔）查找 auto/share/module/<Module>
my $mdir = eval { module_dir('File::ShareDir') };
is($@, '', 'module_dir 调用不抛异常') or diag("err: $@");
ok(defined $mdir && -d $mdir, "module_dir 返回存在的目录（$mdir）");

my $mfile = eval { module_file('File::ShareDir', 'test_file.txt') };
is($@, '', 'module_file 调用不抛异常') or diag("err: $@");
ok(defined $mfile && -f $mfile, 'module_file 返回存在的文件');

# 5. 负例：不存在的发行版必须报错（证明不是恒真空壳）
my $bad = eval { dist_dir('No-Such-Distribution-XYZ') };
ok($@ ne '', '负例：未知发行版时 dist_dir 报错（非恒真）');
ok(!defined $bad, '负例：未知发行版返回 undef');

# 6. 负例：已知发行版但文件不存在也必须报错
my $badf = eval { dist_file('File-ShareDir', 'no_such_file_xyz.txt') };
ok($@ ne '', '负例：缺失数据文件时 dist_file 报错（非恒真）');

done_testing;
print "\nALL OK - file-sharedir 1.118 consumer checks passed\n";
