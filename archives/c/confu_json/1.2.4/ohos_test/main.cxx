// HarmonyOS (OHOS) 专项测试 — confu_json 1.2.4 适配验证
//
// 仅通过 confu_json 已安装的公开头文件 <confu_json/confu_json.hxx> 与公开 API
// (to_json / to_object) 使用该库，验证 OHOS aarch64 (clang 15) 下的实际可编译、
// 可链接、可运行与正确性。覆盖以下适配修复路径：
//   1. enum 序列化（magic_enum）往返
//   2. std::optional / std::vector 往返
//   3. unique_ptr<Base> + BaseToDerivedMapping 映射往返 —— 对应本适配为严格
//      C++20 (clang 15) 补充的 `typename` 修复（to_json.hxx / to_object.hxx
//      中 boost::mpl::at<...>::type 依赖类型）
//
// 构建与运行命令见 README.md；全部检查通过时退出码为 0。
#include <confu_json/confu_json.hxx>

#include <boost/fusion/adapted/struct/adapt_struct.hpp>
#include <boost/mpl/map.hpp>
#include <boost/mpl/pair.hpp>
#include <boost/json/src.hpp>  // header-only：把 boost::json 实现编入本 TU（同上游 test/main.cxx 做法）

#include <cstdlib>
#include <iostream>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace ohos_test
{
enum class Suit
{
  clubs,
  diamonds,
  hearts,
  spades
};

struct Card
{
  int value{};
  Suit suit{};
};

struct Player
{
  std::string name;
  std::vector<Card> cards;
  std::optional<int> rank;
};

struct GameOptionBase
{
  virtual ~GameOptionBase () = default;
  double something{};
};

struct TimedOption : GameOptionBase
{
  int timeoutMs{1000};
};

struct Game
{
  std::vector<Player> players;
  std::optional<Player> mvp;
  std::unique_ptr<GameOptionBase> option;
};

struct UniquePtrEnum
{
  std::unique_ptr<Suit> suit{};
};
} // namespace ohos_test

BOOST_FUSION_ADAPT_STRUCT (ohos_test::Card, value, suit)
BOOST_FUSION_ADAPT_STRUCT (ohos_test::Player, name, cards, rank)
BOOST_FUSION_ADAPT_STRUCT (ohos_test::GameOptionBase, something)
BOOST_FUSION_ADAPT_STRUCT (ohos_test::TimedOption, something, timeoutMs)
BOOST_FUSION_ADAPT_STRUCT (ohos_test::Game, players, mvp, option)
BOOST_FUSION_ADAPT_STRUCT (ohos_test::UniquePtrEnum, suit)

// Base→Derived 映射：命中本适配修复的 boost::mpl 依赖类型路径
using BaseToDerivedMap = boost::mpl::map<boost::mpl::pair<ohos_test::GameOptionBase, ohos_test::TimedOption>>;

int
main ()
{
  int failures = 0;
  auto check = [&failures] (const char *name, bool ok) {
    std::cout << (ok ? "[PASS] " : "[FAIL] ") << name << '\n';
    if (!ok)
      {
        ++failures;
      }
  };

  // 1) enum + vector<Card> + optional<int> 往返
  {
    ohos_test::Game g;
    g.players = { { "alice", { { 7, ohos_test::Suit::hearts } }, 1 },
                  { "bob", { { 2, ohos_test::Suit::clubs } }, std::nullopt } };
    g.mvp = g.players[0];
    auto json = confu_json::to_json (g);
    auto back = confu_json::to_object<ohos_test::Game> (json);
    std::cout << "  json1=" << boost::json::serialize (json) << '\n';
    check ("enum/vector/optional round-trip",
           back.players.size () == 2 && back.players[0].name == "alice"
             && back.players[0].cards[0].suit == ohos_test::Suit::hearts
             && back.mvp.has_value () && back.mvp->name == "alice");
  }

  // 2) unique_ptr<Base> + BaseToDerivedMapping 往返（typename 修复路径）
  {
    ohos_test::Game g;
    g.players = { { "carol", {}, std::nullopt } };
    g.option = std::make_unique<ohos_test::TimedOption> ();
    g.option->something = 3.5;
    auto json = confu_json::to_json<BaseToDerivedMap> (g);
    auto back = confu_json::to_object<ohos_test::Game, BaseToDerivedMap> (json);
    std::cout << "  json2=" << boost::json::serialize (json) << '\n';
    check ("unique_ptr Base->Derived mapping round-trip",
           back.option != nullptr && back.option->something == 3.5);
    auto asTimed = dynamic_cast<ohos_test::TimedOption *> (back.option.get ());
    check ("unique_ptr Derived dynamic_cast", asTimed != nullptr && asTimed->timeoutMs == 1000);
  }

  // 3) unique_ptr<enum> 往返（magic_enum 序列化）
  {
    ohos_test::UniquePtrEnum ue;
    ue.suit = std::make_unique<ohos_test::Suit> (ohos_test::Suit::diamonds);
    auto json = confu_json::to_json (ue);
    auto back = confu_json::to_object<ohos_test::UniquePtrEnum> (json);
    std::cout << "  json3=" << boost::json::serialize (json) << '\n';
    check ("unique_ptr enum round-trip", back.suit && *back.suit == ohos_test::Suit::diamonds);
  }

  std::cout << (failures == 0 ? "ALL OHOS TESTS PASSED" : "OHOS TESTS FAILED") << " (" << failures
            << " failures)\n";
  return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
