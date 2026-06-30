# perl-namespace-clean

## 软件描述

namespace::clean 是一个 Perl pragma，用于在编译周期结束时从当前包中移除之前声明或导入的符号。函数在包自身内部仍可通过名称调用（晚期绑定），但不会作为方法出现在类或实例上。

## 版本历史

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.27-r4 | published | 2026-06-24 | 纯 Perl 模块，编译通过，2099 测试全部通过 |

## 使用说明

```perl
package MyClass;
use strict;
use warnings;

use Some::Module qw(imported_function);

sub my_method { ... }

# 清除所有导入的函数和已定义的函数
# my_method 仍可在包内通过名称调用，但不作为方法
use namespace::clean;

sub another_method {
    my_method();  # 仍可调用
}

# 保留特定函数不被清除
use namespace::clean -except => [qw(meta import)];
```

## 安装方式

通过 cmd-pkgs 公共安装脚本安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-namespace-clean 0.27-r4
```

安装后验证：

```bash
perl -Mnamespace::clean -e 'print "namespace::clean version: ", $namespace::clean::VERSION, "\n"'
# 输出: namespace::clean version: 0.27
```

## 依赖

- Perl >= 5.10
- Package::Stash >= 0.23
- B::Hooks::EndOfScope >= 0.07

## 许可证

Perl 5 Programming Language License (GPL/Artistic)
