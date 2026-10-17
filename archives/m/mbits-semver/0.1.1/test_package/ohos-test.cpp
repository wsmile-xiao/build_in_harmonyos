// HarmonyOS 专项测试 — mbits-semver 0.1.1
// 在 OHOS (aarch64-unknown-linux-ohos) 工具链下验证 semver 语义：
// 解析、比较、prerelease 优先级、compatible_with 兼容矩阵、to_string 往返。
// 独立于上游 semver-test 与 test_package 消费者测试，仅用公开头文件 API。
#include <cstdio>
#include <semver/version.hh>
#include <string>
#include <vector>

static int failures = 0;

static void check(bool cond, const char* what) {
	if (!cond) {
		std::fprintf(stderr, "FAIL: %s\n", what);
		++failures;
	} else {
		std::printf("PASS: %s\n", what);
	}
}

int main() {
	// 1) 解析与 getter
	{
		auto v = semver::project_version{"1.2.3-alpha.1+build.5"};
		check(v.get_major() == 1, "parse major=1");
		check(v.get_minor() == 2, "parse minor=2");
		check(v.get_patch() == 3, "parse patch=3");
		check(v.to_string().find("1.2.3") != std::string::npos, "to_string contains 1.2.3");
	}
	// 2) 数值比较 (SemVer 11.4.1: 数字标识符按数值比较)
	{
		check(semver::project_version{"2.0.0"} > semver::project_version{"10.0.0"} == false,
		      "2.0.0 < 10.0.0 numerically");
		check(semver::project_version{"1.0.0-alpha"} < semver::project_version{"1.0.0"},
		      "prerelease < release");
		check(semver::project_version{"1.0.0-alpha"} < semver::project_version{"1.0.0-alpha.1"},
		      "alpha < alpha.1");
		check(semver::project_version{"1.0.0-alpha.1"} < semver::project_version{"1.0.0-alpha.beta"},
		      "alpha.1 < alpha.beta");
		check(semver::project_version{"1.0.0-beta.11"} < semver::project_version{"1.0.0-rc.1"},
		      "beta.11 < rc.1");
		check(semver::project_version{"1.0.0-rc.1"} < semver::project_version{"1.0.0"},
		      "rc.1 < release");
	}
	// 3) 兼容性矩阵 (compatible_with)
	{
		// 编译期版本 0.1.1-beta：major=0 时仅完全相同才兼容
		check(semver::version.compatible_with(semver::get_version()), "self compatible");
		check(!semver::version.compatible_with(semver::project_version{"1.3.0-beta.5"}),
		      "0.1.1-beta incompatible with 1.3.0");
		check(semver::project_version{"0.1.1-beta"}.compatible_with(
		          semver::project_version{"0.1.1-beta"}),
		      "same 0.1.1-beta compatible");
		check(!semver::project_version{"0.1.1-beta"}.compatible_with(
		          semver::project_version{"0.1.2-beta"}),
		      "0.1.1-beta incompatible with 0.1.2");
	}
	// 4) build 元数据不影响优先级
	{
		check(semver::project_version{"1.0.0+build.1"} == semver::project_version{"1.0.0+build.2"},
		      "build metadata ignored in equality");
	}
	if (failures == 0) {
		std::printf("OHOS semver test: ALL PASSED\n");
		return 0;
	}
	std::printf("OHOS semver test: %d FAILURES\n", failures);
	return 1;
}
