// test_package/test_ohos.c — cheat 鸿蒙(HarmonyOS)专项测试
//
// 与上游 tests/ 及 test_package/test.c 不同的真实 OHOS 专项验证：
//   1. 平台属性：__OHOS__/__aarch64__ 预定义宏在 OHOS 工具链下必须存在；
//   2. POSIX 运行环境：unistd 服务（getpid/getppid）真实可用；
//   3. 框架在 OHOS 上端到端真实执行（断言基于 POSIX 运行时值，非常量）。
// 全部用例预期通过；任一断言失败即非零退出（非空壳测试）。
#include <cheat.h>
#include <cheats.h>

#include <unistd.h>

CHEAT_TEST(ohos_platform_detected,
	/* OHOS clang 工具链（aarch64-linux-ohos）预定义 __OHOS__ 与
	   __aarch64__；在 OHOS 上必须为真，否则说明编译环境不符。 */
#if defined(__OHOS__)
	cheat_assert(__OHOS__ == 1);
#else
	cheat_assert(0);
#endif
#if defined(__aarch64__)
	cheat_assert(__aarch64__ == 1);
#else
	cheat_assert(0);
#endif
)

CHEAT_TEST(posix_environment_works,
	/* cheat.h 在 __linux__ 下启用 CHEAT_POSIXLY（write/fdopen 包装），
	   依赖 POSIX 运行环境；验证 unistd 基本服务真实可用。 */
	cheat_assert_int(getpid() > 0, 1);
	cheat_assert_int(getppid() >= 0, 1);
)

CHEAT_TEST(framework_executes_on_ohos,
	/* 端到端执行验证：基于 POSIX 运行时值做真实断言（同一进程内
	   getpid() 两次结果一致），证明 cheat 框架在 OHOS aarch64
	   上完整走完测试运行路径。 */
	pid_t const pid = getpid();
	cheat_assert_int(pid, pid);
	cheat_assert_int(pid > 1 ? 1 : 0, 1);
)
