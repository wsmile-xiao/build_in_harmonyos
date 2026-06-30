# perl-mixin-event-dispatch

Mixin methods for simple event/message dispatch framework.

## 简介

Mixin::Event::Dispatch 是一个 Perl 事件分发框架，提供：
- **Mixin 模式事件订阅**：通过 `use parent qw(Mixin::Event::Dispatch)` 轻松为任意类添加事件能力
- **多处理器支持**：同一事件可注册多个处理器，按注册顺序执行
- **独立事件总线**：`Mixin::Event::Dispatch::Bus` 提供不继承 mixin 的事件分发
- **函数式 API**：`Mixin::Event::Dispatch::Methods` 提供函数式调用接口

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 2.000 | published | 2026-06-18 | 纯 Perl 模块，含 List::UtilsBy 依赖 |

## 鸿蒙平台兼容性

- **模块类型**: 纯 Perl（无 XS 组件）
- **SELinux 限制**: 无（纯 Perl 模块不受 HMDFS 限制）
- **运行时依赖**: List::UtilsBy 0.12（已包含在打包产物中）
- **安装方式**: 解压 tar.gz 到 `$PREFIX` 目录即可

## 安装

```bash
# 通过 cmd-pkgs 安装（推荐）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-mixin-event-dispatch 2.000

# 手动安装
tar xzf perl-mixin-event-dispatch-2.000-ohos-aarch64.tar.gz -C $PREFIX
```

## 使用示例

```perl
use Mixin::Event::Dispatch;

# 为类添加事件能力
package MyApp {
    use parent qw(Mixin::Event::Dispatch);
}

my $app = MyApp->new();
$app->subscribe_to_event(on_data => sub {
    my ($self, $event) = @_;
    print "Received data: $event->{data}\n";
});
$app->invoke_event(on_data => { data => "hello" });
```

## 许可证

Perl (Artistic License 2.0)
