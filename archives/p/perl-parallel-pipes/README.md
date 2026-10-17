# perl-parallel-pipes

Parallel processing using pipe(2) for communication and synchronization.

## 软件信息

- **官网**: https://metacpan.org/pod/Parallel::Pipes
- **源码**: https://github.com/skaji/Parallel-Pipes
- **许可证**: GPL-1.0-or-later OR Artistic-1.0
- **分类**: perl
- **构建系统**: Module::Build::Tiny (Build.PL)

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.201 | published | 2026-07-06 | 纯 Perl 模块，全功能测试通过 |

## 软件描述

Parallel::Pipes 提供基于 pipe(2) 的并行处理能力，通过 fork 创建子进程，使用管道进行进程间通信和数据同步。被 App::cpm（快速 CPAN 模块安装器）等工具使用。

### 主要功能

- **Parallel::Pipes** — 低级接口，提供 fork + pipe + select 并行处理
- **Parallel::Pipes::App** — 高级接口，提供 `map()` 和 `run()` 方法

### 技术原理

- 使用 `fork()` 创建工作进程
- 使用 `pipe(2)` 在父子进程间通信
- 使用 `IO::Select` 检测管道就绪状态
- 使用 `Storable` 序列化/反序列化传输数据
- 单进程模式 (`num=1`) 使用 NoFork 实现，无需 fork

## 运行依赖

- perl (≥ 5.008001)
- Storable (Perl 核心模块)
- IO::Handle (Perl 核心模块)
- IO::Select (Perl 核心模块)

## 编译依赖

无额外编译依赖。所有依赖均为 Perl 核心模块。

## 使用说明

### 通过 Conan 安装

```bash
conan install --requires=perl-parallel-pipes/0.201@ohpcd/stable
```

### 基本使用

```perl
use Parallel::Pipes;

my $pipes = Parallel::Pipes->new(3, sub {
    my $task = shift;
    return $task * 2;
});

# 写入任务
my @ready = $pipes->is_ready;
$ready[0]->write(42);

# 读取结果
my $result = $ready[0]->read;  # 84

$pipes->close;
```

### 使用 App 接口

```perl
use Parallel::Pipes::App;

my @result = Parallel::Pipes::App->map(
    num => 4,
    work => sub { my $n = shift; $n ** 2 },
    tasks => [1, 2, 3, 4, 5],
);
# @result = (1, 4, 9, 16, 25)
```

## 鸿蒙平台兼容性

| 功能 | 状态 | 说明 |
|------|------|------|
| fork() | ✅ | 正常工作 |
| pipe(2) | ✅ | 正常工作 |
| IO::Select | ✅ | 正常工作 |
| Storable | ✅ | 正常工作 |
| 多进程并行 | ✅ | 完全可用 |
| idle 回调 | ✅ | 完全可用 |
| 大数据传输 | ✅ | 100KB+ 无丢失 |

**无需特殊处理**：纯 Perl 模块不涉及 C/XS 编译，无 CRT 文件、ELF 签名或 SELinux 限制问题。

## 测试覆盖

| 测试类型 | 测试数 | 断言数 | 结果 |
|---------|--------|--------|------|
| 上游测试 | 5 | 46 | ✅ ALL PASS |
| 平台兼容性 | 5 | 5 | ✅ ALL PASS |
| 综合功能 | 7 | 7 | ✅ ALL PASS |
| Conan test_package | 1 | 1 | ✅ PASS |
| **总计** | **18** | **59** | **ALL PASS** |

---
*OpenHarmony 编译归档 · 2026-07-06*
