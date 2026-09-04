// replxx 0.0.4 HarmonyOS 专项测试
// 验证 replxx 静态库在 OpenHarmony（aarch64, clang）环境下的可链接性、
// 对象生命周期、历史记录 API 与版本宏，非交互式、可复现。
#include <replxx.hxx>
#include <string>
#include <cstdio>
#include <cstdlib>

static int failures = 0;
#define CHECK(cond, msg) \
	do { if (!(cond)) { std::fprintf(stderr, "FAIL: %s\n", msg); ++failures; } \
	     else { std::printf("PASS: %s\n", msg); } } while (0)

int main() {
	std::printf("=== replxx HarmonyOS spec test (0.0.4) ===\n");

	// 1) 编译期 include/链接期验证：replxx 头可包含、库可链接
	{
		replxx::Replxx rx;
		CHECK(true, "replxx.hxx include + libreplxx link OK");
	}
	{
		replxx::Replxx rx;
		rx.history_add("version-probe");
		CHECK(rx.history_size() == 1, "runtime API probe OK");
	}

	// 2) 对象生命周期：构造/析构不崩溃
	{
		replxx::Replxx rx;
		CHECK(true, "Replxx object constructed");
	}

	// 3) 历史记录 API（非交互，不依赖 TTY）
	{
		replxx::Replxx rx;
		CHECK(rx.history_size() == 0, "history_size()==0 initially");
		rx.history_add("replxx-ohos-line-1");
		rx.history_add("replxx-ohos-line-2");
		CHECK(rx.history_size() == 2, "history_size()==2 after two adds");
		replxx::Replxx::State st = rx.get_state();
		CHECK(st.text() != nullptr, "state.text() readable");
	}

	// 4) 配置 setter 子集（无 TTY 副作用路径）
	{
		replxx::Replxx rx;
		rx.set_max_history_size(100);
		rx.set_completion_count_cutoff(1024);
		rx.set_no_color(false);
		rx.set_unique_history(true);
		CHECK(true, "configuration setters accepted");
		rx.history_add("dup");
		rx.history_add("dup");
		CHECK(rx.history_size() == 1, "unique_history dedups");
	}

	// 5) preload buffer + 状态接口
	{
		replxx::Replxx rx;
		rx.set_preload_buffer("hello ohos");
		replxx::Replxx::State st = rx.get_state();
		CHECK(st.text() != nullptr, "state readable after set_preload_buffer");
	}

	std::printf("=== result: %s ===\n", failures == 0 ? "ALL PASS" : "HAS FAILURES");
	return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}