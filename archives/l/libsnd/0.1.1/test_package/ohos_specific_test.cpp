// libsnd HarmonyOS 专项测试用例 — OHOS 平台真实可执行验证
// 目的：验证 libsnd 在 OpenHarmony PC (aarch64, musl libc, OHOS 运行时) 下
//       DSP 数值行为正确，且静态库可被消费者正常链接使用。
// 独立于上游 gtest 套件（上游测试消费 snd::approx/interpolation 等，
// 本用例聚焦 OHOS 平台下的库行为 + 运行时特性）。
#include <snd.h>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <sys/utsname.h>

static int failures = 0;

static void check(bool ok, const char *what) {
  std::printf("  [%s] %s\n", ok ? "PASS" : "FAIL", what);
  if (!ok) failures++;
}

int main() {
  std::printf("== libsnd HarmonyOS 专项测试 ==\n");

  // OHOS 运行时环境探针：确认在目标平台执行（区别于宿主 Linux）
  struct utsname u{};
  if (uname(&u) == 0) {
    std::printf("  sysname=%s release=%s machine=%s\n", u.sysname, u.release, u.machine);
    check(std::strstr(u.machine, "aarch64") != nullptr, "machine is aarch64 (OHOS PC arm64)");
  } else {
    check(false, "uname() 失败");
  }

  // 1) 静态库链接与符号存在：snd::approx 域 API
  double si = snd::sineApprox7odd<double>(0.5);   // <snd.h> 内 approx 实现
  check(std::abs(si - 1.0) < 1e-4, "sinApprox7odd(0.5) ≈ 1.0");

  // 2) denormal 处理（OHOS musl 运行时通常无 FTZ 强制，库应自行处理）
  std::printf("  denormal_min = %.6e isDenormal=%d\n",
              std::numeric_limits<double>::denorm_min(),
              snd::isDenormal(std::numeric_limits<double>::denorm_min()) ? 1 : 0);
  check(snd::isDenormal(std::numeric_limits<double>::denorm_min()), "isDenormal(denorm_min) == true");
  check(!snd::isDenormal(1.0), "isDenormal(1.0) == false");
  double cancelled = snd::denormalCancel(std::numeric_limits<double>::denorm_min());
  check(cancelled == 0.0, "denormalCancel(denorm_min) == 0.0");

  // 3) interpolation 公开 API 数值行为
  check(snd::interp_linear(0.5, 0.0, 1.0) == 0.5, "interp_linear(0.5,0,1) == 0.5");

  // 4) FlipFlop 状态机
  snd::FlipFlop ff(false);
  bool b1 = ff.tick();
  bool b2 = ff.tick();
  check(b1 == true && b2 == false, "FlipFlop 状态翻转");

  // 5) 编译期可用性：库可按 C++17 消费（头文件包含即验证）
  check(snd::sineApprox7odd<double>(0.0) == 0.0, "sinApprox7odd(0)==0");

  std::printf("== 结果: %s (failures=%d) ==\n", failures == 0 ? "PASS" : "FAIL", failures);
  return failures == 0 ? 0 : 1;
}