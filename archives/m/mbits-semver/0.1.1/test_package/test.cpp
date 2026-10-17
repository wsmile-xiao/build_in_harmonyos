#include <cstdio>
#include <semver/version.hh>
#include <string>

int main() {
	// 消费者验证：仅通过库导出的公开头文件调用公开 API
	auto const parsed = semver::project_version{"1.2.3-alpha.1+build.5"};
	if (parsed.get_major() != 1 || parsed.get_minor() != 2 || parsed.get_patch() != 3) {
		std::fprintf(stderr, "FAIL: parse major/minor/patch\n");
		return 1;
	}
	auto const text = parsed.to_string();
	if (text.empty()) {
		std::fprintf(stderr, "FAIL: to_string empty\n");
		return 2;
	}
	std::printf("mbits-semver consumer: parsed=%s to_string=%s\n",
	            parsed.get_major() ? "ok" : "bad", text.c_str());

	// 运行时版本兼容性判断（公开 API）
	bool self_compat = semver::version.compatible_with(semver::get_version());
	bool cross_compat = semver::version.compatible_with(semver::project_version{"0.1.1-beta"});
	std::printf("self_compatible=%s\n", self_compat ? "true" : "false");
	std::printf("cross_compatible=%s\n", cross_compat ? "true" : "false");
	if (!self_compat) {
		std::fprintf(stderr, "FAIL: self compatibility must hold\n");
		return 3;
	}
	return 0;
}
