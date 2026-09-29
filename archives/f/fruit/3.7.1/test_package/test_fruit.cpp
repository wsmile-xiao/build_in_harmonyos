// test_fruit.cpp — 消费者冒烟验证（fruit 3.7.1）
//
// 仅使用 fruit 已安装/导出的公开头文件与公开 API（<fruit/fruit.h>）：
// Component / createComponent / bind / Injector / get，验证第三方使用者
// 可以编译、链接、调用并正常运行该 DI 框架。
//
// 注意：fruit 基于 typeid 做类型键，参与 DI 的类必须位于命名空间作用域
// （非匿名命名空间、非局部类），且接口/实现类型需用具名类型。
#include <fruit/fruit.h>

#include <cassert>
#include <iostream>
#include <string>

struct Greeter {
  virtual ~Greeter() = default;
  virtual std::string greet() const = 0;
};

struct GreeterImpl : public Greeter {
  // fruit 要求实现类显式标注可注入构造函数（INJECT 宏），默认构造函数
  // 不会被 bind<I,C> 自动识别。
  INJECT(GreeterImpl()) = default;

  std::string greet() const override { return "hello from fruit"; }
};

fruit::Component<Greeter> getGreeterComponent() {
  return fruit::createComponent().bind<Greeter, GreeterImpl>();
}

int main() {
  fruit::Injector<Greeter> injector(getGreeterComponent);
  Greeter* greeter = injector.get<Greeter*>();
  assert(greeter != nullptr);

  const std::string msg = greeter->greet();
  assert(msg == "hello from fruit");

  // 同一 Injector 二次注入应返回同一实例（单例语义）。
  Greeter* greeter2 = injector.get<Greeter*>();
  assert(greeter2 == greeter);

  std::cout << "fruit consumer OK: " << msg << std::endl;
  return 0;
}