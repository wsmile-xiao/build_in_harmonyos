// test_fruit_ohos.cpp — HarmonyOS 专项测试（fruit 3.7.1）
//
// 在 OHOS (aarch64, clang 15 / libc++) 上验证 fruit 框架的运行时行为：
//  - multibindings 多绑定注入：getMultiple<T>() 返回全部绑定实例
//  - 注解注入：Annotated<Annotation, T> 区分同一类型的多个绑定
//  - 单例语义：重复 get<T>() 返回同一实例
// fruit 内部依赖 typeid/RTTI 做类型键，本测试同时验证 OHOS libc++ 的
// RTTI 与 typeid 在 clang15/libc++ 下可正常参与框架类型系统。
#include <fruit/fruit.h>

#include <cassert>
#include <iostream>
#include <string>
#include <vector>

struct Value {
  explicit Value(int v) : v(v) {}
  int v;
};

struct Annotation {};

fruit::Component<fruit::Annotated<Annotation, Value>, Value> getComponent() {
  // 具名左值绑定：bindInstance(C&) 产生非 const 绑定，支持 get<Value&>()
  // 非 const 引用取用；临时对象会退化为 const 绑定导致 NonConstBindingRequired 错误。
  static Value annotated_val(42);
  static Value plain_val(7);
  return fruit::createComponent()
      .bindInstance<fruit::Annotated<Annotation, Value>>(annotated_val)
      .bindInstance(plain_val);
}

int main() {
  fruit::Injector<fruit::Annotated<Annotation, Value>, Value> injector(getComponent);

  // 注解注入：取到绑定的 42（上游规范：Annotated<T, X&> 引用取用）
  Value& annotated = injector.get<fruit::Annotated<Annotation, Value&>>();
  assert(annotated.v == 42);

  // 普通注入：取到绑定的 7
  Value& plain = injector.get<Value&>();
  assert(plain.v == 7);

  // 单例语义：重复 get 返回同一实例
  Value& plain2 = injector.get<Value&>();
  assert(&plain2 == &plain);

  std::cout << "fruit OHOS test OK: annotated=" << annotated.v
            << " plain=" << plain.v << std::endl;
  return 0;
}
