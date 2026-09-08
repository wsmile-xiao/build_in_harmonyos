// test_package consumer test for tinyfsm 0.3.3.
// Exercises the real public API of the header-only FSM library:
// Fsm 派生状态机声明、FSM_INITIAL_STATE、start()、事件 dispatch、
// 状态转移（transit）与 is_in_state 断言。对应上游 simple_switch 示例逻辑。
#include <tinyfsm.hpp>

#include <cstdio>

// 1. 事件声明
struct Toggle : tinyfsm::Event { };

class Off;  // 前向声明：On::react 中 transit<Off>() 需要

// 2. 状态机基类
class Switch : public tinyfsm::Fsm<Switch>
{
public:
  virtual void react(Toggle const &) { }
  virtual void entry(void) { }   /* 部分状态有 entry 动作 */
  void exit(void) { }            /* 无 exit 动作 */
};

// 3. 状态声明与转移
class On : public Switch
{
public:
  void entry() override { }
  void react(Toggle const &) override { transit<Off>(); }
};

class Off : public Switch
{
public:
  void entry() override { }
  void react(Toggle const &) override { transit<On>(); }
};

FSM_INITIAL_STATE(Switch, Off)

// 4. 主流程：start → 初始状态断言 → 两次 dispatch(Toggle) → 状态切换断言
int main(void)
{
  Switch::start();
  if (!Switch::is_in_state<Off>())
  {
    std::printf("FAIL: initial state is not Off\n");
    return 1;
  }

  Toggle toggle;
  Switch::dispatch(toggle);           /* Off -> On */
  if (!Switch::is_in_state<On>())
  {
    std::printf("FAIL: after toggle 1, state is not On\n");
    return 2;
  }

  Switch::dispatch(toggle);           /* On -> Off */
  if (!Switch::is_in_state<Off>())
  {
    std::printf("FAIL: after toggle 2, state is not Off\n");
    return 3;
  }

  std::printf("tinyfsm 0.3.3 ok: Off -> On -> Off transitions verified\n");
  return 0;
}