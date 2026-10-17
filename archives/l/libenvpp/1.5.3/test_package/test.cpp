#include <cstdlib>
#include <iostream>

#include <libenvpp/env.hpp>

int main()
{
	// 真实调用 libenvpp API：注册环境变量、注入并解析验证 (R34)
	auto pre = env::prefix("TESTENVPP");

	const auto num_id = pre.register_variable<unsigned int>("NUM_THREADS");
	const auto flag_id = pre.register_variable<bool>("ENABLE_FOO");

	const auto parsed = pre.parse_and_validate({{"TESTENVPP_NUM_THREADS", "4"}, {"TESTENVPP_ENABLE_FOO", "true"}});

	if (!parsed.ok()) {
		std::cerr << "parse failed: " << parsed.error_message() << std::endl;
		return EXIT_FAILURE;
	}

	if (parsed.get(num_id) != 4U) {
		std::cerr << "NUM_THREADS mismatch" << std::endl;
		return EXIT_FAILURE;
	}
	if (!parsed.get(flag_id)) {
		std::cerr << "ENABLE_FOO mismatch" << std::endl;
		return EXIT_FAILURE;
	}

	std::cout << "libenvpp 1.5.3 test_package: OK (NUM_THREADS=" << parsed.get(num_id).value()
	          << ", ENABLE_FOO=" << parsed.get(flag_id).value() << ")" << std::endl;
	return EXIT_SUCCESS;
}