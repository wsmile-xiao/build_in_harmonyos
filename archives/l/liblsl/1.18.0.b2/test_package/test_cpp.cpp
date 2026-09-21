// test_package 消费者测试 —— liblsl C++ API（R34：必须实质调用被测包的 API）。
//
// 与 test_c.c 互补：这里走 lsl_cpp.h 的 RAII 包装（lsl::stream_info /
// lsl::stream_outlet / lsl::stream_inlet），验证安装出的 C++ 头文件能被 C++17
// 消费者直接包含、模板 push/pull 能实例化并与 liblsl.so 正确链接、运行。
#include <lsl_cpp.h>

#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

int g_checks = 0;
int g_failed = 0;

void check(bool cond, const char *msg) {
	++g_checks;
	if (cond) {
		std::printf("ok   - %s\n", msg);
	} else {
		++g_failed;
		std::printf("FAIL - %s\n", msg);
	}
}

} // namespace

int main() {
	// ── 1. 库标识 ──
	check(lsl::library_version() == 118, "lsl::library_version() == 118");
	check(std::strstr(lsl::library_info(), "1.18.0.b2") != nullptr,
	      "lsl::library_info() 含 1.18.0.b2");
	check(lsl::local_clock() > 0.0, "lsl::local_clock() > 0");
	check(lsl::protocol_version() == 110, "lsl::protocol_version() == 110");

	// ── 2. stream_info（C++ 值语义 + XML 往返）──
	lsl::stream_info info("liblsl-consumer-cpp", "Markers", 3, lsl::IRREGULAR_RATE,
	                      lsl::cf_string, "liblsl-cpp-test-uid");
	check(info.channel_count() == 3, "stream_info::channel_count() == 3");
	check(info.channel_format() == lsl::cf_string, "stream_info::channel_format() == cf_string");
	check(info.name() == "liblsl-consumer-cpp", "stream_info::name()");
	check(info.source_id() == "liblsl-cpp-test-uid", "stream_info::source_id()");

	// fresh stream_info 的 uid 为空；空 uid 的 XML 反序列化出来是无效对象
	// （字段读取全为 0）。先 reset_uid() 再往返。
	const std::string uid = info.reset_uid();
	check(!uid.empty(), "stream_info::reset_uid() 生成非空 uid");

	std::string xml = info.as_xml();
	check(xml.find("liblsl-consumer-cpp") != std::string::npos, "stream_info::as_xml() 含流名");
	lsl::stream_info round = lsl::stream_info::from_xml(xml);
	check(round.uid() == uid, "from_xml() 往返后 uid 一致");
	check(round.channel_count() == 3, "from_xml() 往返后 channel_count 一致");

	// ── 3. 真实数据通路：outlet → inlet（本机回环，C++ 模板 push/pull）──
	lsl::stream_outlet outlet(info);
	try {
		lsl::stream_inlet inlet(info);
		inlet.open_stream(5.0);
		// outlet 会为自己的 stream_info 副本分配 uid（与传入的 info 句柄上的 uid
		// 不是同一个），因此要与 outlet.info() 比较，而不是构造参数那份。
		check(inlet.info(5.0).uid() == outlet.info().uid(),
		      "inlet.info().uid() 与 outlet.info().uid() 一致");
		check(outlet.wait_for_consumers(5.0), "outlet.wait_for_consumers() 观测到消费者");

		std::vector<std::string> sent{"alpha", "beta", "gamma"};
		outlet.push_sample(sent.data());
		std::vector<std::string> got;
		double ts = inlet.pull_sample(got, 5.0);
		check(ts > 0.0 && got.size() == 3, "inlet.pull_sample() 收到 3 通道样本");
		if (got.size() == 3) {
			check(got[0] == "alpha" && got[1] == "beta" && got[2] == "gamma",
			      "拉取到的字符串样本与推送一致");
		}
		inlet.close_stream();
	} catch (const std::exception &e) {
		check(false, "C++ 数据通路未抛异常");
		std::printf("      异常: %s\n", e.what());
	}

	std::printf("ASSERTIONS: %d FAILED: %d\n", g_checks, g_failed);
	if (g_failed) {
		std::printf("RESULT: FAIL\n");
		return 1;
	}
	std::printf("RESULT: PASS\n");
	return 0;
}
