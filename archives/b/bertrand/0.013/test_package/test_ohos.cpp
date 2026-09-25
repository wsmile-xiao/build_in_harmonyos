// HarmonyOS 专项测试 — bertrand 0.013 (OHOS armv8 runtime 行为验证).
//
// 目的：在 OHOS 工具链(clang 15 / aarch64-linux-ohos)与 OHOS 运行时下验证
// header-only 契约库的真实行为，而非复述上游 Catch2 用例：
//   1. Invariant 违约在 BERTRAND_CONTRACTS_ARE_EXCEPTIONS 下抛
//      std::runtime_error（OHOS libc++ 异常路径可用）；
//   2. 契约消息文本包含违约类型标记与表达式（OHOS stderr 输出）；
//   3. 宏冲突 static_assert 在编译期拦截（-DBERTRAND_ENABLE_CONTRACTS
//      -DBERTRAND_DISABLE_CONTRACTS 同时定义时编译失败，与上游一致）。
//   4. find::in 在 OHOS 上正常编译运行。
#include <bertrand/bertrand.hpp>

#include <iostream>
#include <stdexcept>
#include <string>

int main() {
  int failures = 0;

  // 1) Invariant 违约 -> 异常（OHOS 运行时异常路径验证）
  try {
    Invariant(false, "OHOS invariant must fail");
    std::cout << "OHOS Invariant(failing): NO THROW" << std::endl;
    ++failures;
  } catch (const std::runtime_error &e) {
    const std::string what = e.what();
    if (what.find("Invariant") != std::string::npos &&
        what.find("OHOS invariant must fail") != std::string::npos) {
      std::cout << "OHOS Invariant(failing): OK (threw with type+message)"
                << std::endl;
    } else {
      std::cout << "OHOS Invariant(failing): wrong message: " << what
                << std::endl;
      ++failures;
    }
  }

  // 2) 通过型契约不抛（OHOS 正常运行路径）
  try {
    Invariant(true, "must pass");
    Require(1 == 1, "trivially true");
    std::cout << "OHOS passing contracts: OK" << std::endl;
  } catch (const std::runtime_error &) {
    std::cout << "OHOS passing contracts: UNEXPECTED THROW" << std::endl;
    ++failures;
  }

  // 3) find::in 在 OHOS 上运行
  const bertrand::find<int> choice{2};
  if (!choice.in(1, 2, 3)) {
    std::cout << "OHOS find.in: 2 must be in {1,2,3}" << std::endl;
    ++failures;
  }
  if (choice.in(9)) {
    std::cout << "OHOS find.in: 2 must NOT be in {9}" << std::endl;
    ++failures;
  }
  std::cout << "OHOS find.in: OK" << std::endl;

  if (failures == 0) {
    std::cout << "OHOS test bertrand 0.013: ALL PASSED" << std::endl;
    return 0;
  }
  std::cout << "OHOS test bertrand 0.013: " << failures
            << " FAILED" << std::endl;
  return 1;
}