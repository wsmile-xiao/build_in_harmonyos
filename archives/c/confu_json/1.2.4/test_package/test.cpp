// 消费者用例 (test_package) — confu_json 1.2.4
//
// 模拟业务上层组件：仅通过 confu_json 已安装/导出的公开头文件
// <confu_json/confu_json.hxx> 与公开 API (to_json / to_object) 使用该库，
// 编译、链接并运行一次有业务意义的 JSON 往返（enum / optional / vector），
// 以可观察结果（往返后字段一致）验证第三方消费者可正常使用。
#include <confu_json/confu_json.hxx>

#include <boost/fusion/adapted/struct/adapt_struct.hpp>
#include <boost/json/src.hpp>  // header-only：boost::json 实现编入本 TU

#include <cstdlib>
#include <iostream>
#include <optional>
#include <string>
#include <vector>

namespace consumer
{
enum class Color
{
  red,
  green,
  blue
};

struct Item
{
  std::string name;
  int count{};
  Color color{};
  std::optional<std::string> note;
};

struct Cart
{
  std::vector<Item> items;
};
} // namespace consumer

BOOST_FUSION_ADAPT_STRUCT (consumer::Item, name, count, color, note)
BOOST_FUSION_ADAPT_STRUCT (consumer::Cart, items)

int
main ()
{
  consumer::Cart cart;
  cart.items = { { "apple", 3, consumer::Color::green, std::nullopt },
                 { "lemon", 1, consumer::Color::red, "sour" } };

  auto json = confu_json::to_json (cart);
  auto back = confu_json::to_object<consumer::Cart> (json);

  bool ok = back.items.size () == 2 && back.items[0].name == "apple" && back.items[0].count == 3
            && back.items[0].color == consumer::Color::green && back.items[1].name == "lemon"
            && back.items[1].color == consumer::Color::red && back.items[1].note
            && *back.items[1].note == "sour";

  std::cout << (ok ? "consumer round-trip OK: " : "consumer round-trip FAILED: ")
            << boost::json::serialize (json) << '\n';
  return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
