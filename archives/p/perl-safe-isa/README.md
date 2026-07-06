# perl-safe-isa

Call isa, can, does and DOES safely on things that may not be objects.

## 简介

Safe::Isa 提供了安全的 `isa`/`can`/`does`/`DOES` 调用方式，用于处理可能不是对象的数据。
模块使用 `Scalar::Util::blessed()` 判断目标是否为 blessed 对象，仅对对象调用方法，
非对象安全返回 false 而不抛异常。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.000010 | published | 2026-06-30 |

## 构建系统

- **类型**: Perl ExtUtils::MakeMaker (Makefile.PL)
- **编译方式**: `perl Makefile.PL INSTALLDIRS=site && make -j1 && make install`
- **纯 Perl 模块**: 无 XS 代码，无原生编译

## 鸿蒙适配

- **平台**: OpenHarmony 6.0 (aarch64)
- **Perl**: 5.42.0
- **无需补丁**: 源码无需任何修改即可编译
- **无 XS 依赖**: 不受鸿蒙 .so 加载限制影响
- **Conan 引用**: `perl-safe-isa/1.000010`

## 导出变量

| 变量 | 用途 |
|------|------|
| `$_isa` | 安全调用 `$obj->isa($class)` |
| `$_can` | 安全调用 `$obj->can($method)` |
| `$_does` | 安全调用 `$obj->does($role)` |
| `$_DOES` | 安全调用 `$obj->DOES($role)` |
| `$_call_if_object` | 对对象调用方法，非对象返回 undef |
| `$_call_if_can` | 方法存在时调用，否则返回 undef |

## 使用示例

```perl
use Safe::Isa;

# 安全的 isa 检查 — 不会因 undef 或非对象抛异常
my $maybe_obj = get_something();  # 可能是 undef
if ($maybe_obj->$_isa("MyClass")) {
    # 仅当 $maybe_obj 是 MyClass 的实例时执行
}

# 安全的方法调用
$result = $maybe_obj->$_call_if_can("process");
```

## 依赖

- perl 5.006+
- Scalar::Util (核心模块)
- Exporter >= 5.57 (核心模块)
