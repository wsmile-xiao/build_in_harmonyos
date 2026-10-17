// test_package for cpp-taskflow 3.8.0
// 真实消费被测包 API：创建任务图、定义依赖、执行并断言结果（R34 实质测试）。
#include <taskflow/taskflow.hpp>
#include <cassert>
#include <iostream>

int main() {
  // 最小任务图：a 先于 b，验证依赖序与工作窃取执行
  tf::Executor executor(2);
  tf::Taskflow taskflow;

  int x = 0;
  auto a = taskflow.emplace([&x]() { x = 1; });
  auto b = taskflow.emplace([&x]() { x += 10; });
  a.precede(b);

  executor.run(taskflow).wait();

  // NDEBUG/Release 下 assert 会被编译掉，必须用运行时检查保证实质验证（R34）
  if (x != 11 || taskflow.num_tasks() != 2 || executor.num_workers() != 2) {
    std::cerr << "cpp-taskflow test_package FAILED: x=" << x
              << " tasks=" << taskflow.num_tasks()
              << " workers=" << executor.num_workers() << std::endl;
    return 1;
  }

  std::cout << "cpp-taskflow test_package OK: x=" << x
            << " tasks=" << taskflow.num_tasks()
            << " workers=" << executor.num_workers() << std::endl;
  return 0;
}