// test_package 消费者验证：实际调用 jsonifier 0.9.97 公开 API 编译并运行
// （R34，非空壳测试）。
//
// 说明：
// 1) 0.9.97 的解析/序列化以库原生支持类型（vector/map/string/标量等）为主；
//    任意自定义结构需上游反射注册机制，故此处使用原生类型做端到端往返验证。
// 2) validateJson 数字路径在 0.9.97 存在上游缺陷（consumeSign 对无符号数字
//    返回 false，任何平台皆然），已记入测试台账与 notes.md。
// 3) std::map 序列化在 0.9.97 存在上游缺陷（输出缺尾部 '}'，clang-15 与
//    clang-22 双工具链一致复现，与 OHOS 适配补丁无关——见 notes.md），
//    故 map 仅验证 parseJson 读取正确性，不断言其 serializeJson 输出。
// 4) validateJson 完整实例化会触发 OHOS SDK clang-15 前端的 IRGen 段错误
//    （工具链 bug，clang-22 编译运行正常），故消费者验证以 parse/serialize
//    路径覆盖（二者在本工具链下编译并运行通过）。

#include <jsonifier/Index.hpp>

#include <cstdio>
#include <map>
#include <string>
#include <vector>

int main() {
	jsonifier::jsonifier_core parser{};

	// 1) serializeJson：vector<int> -> JSON 文本
	std::vector<int> v{ 1, 2, 3 };
	auto out = parser.serializeJson(v);
	if (out.size() == 0) {
		std::printf("serializeJson: FAIL (empty output)\n");
		return 1;
	}
	std::printf("serializeJson ok: %s\n", std::string(out.data(), out.size()).c_str());

	// 2) parseJson：JSON 文本 -> map<string,int>（键序、整数值）
	std::map<std::string, int> m;
	std::string in = R"({"a":1,"b":2,"c":3})";
	if (!parser.parseJson(m, in)) {
		std::printf("parseJson(map): FAIL\n");
		return 1;
	}
	if (m.size() != 3 || m["a"] != 1 || m["b"] != 2 || m["c"] != 3) {
		std::printf("parseJson(map): FAIL (values mismatch)\n");
		return 1;
	}
	std::printf("parseJson(map) ok: size=%zu\n", m.size());

	// 3) vector 往返：serializeJson -> parseJson 比对
	std::vector<int> v2;
	if (!parser.parseJson(v2, std::string(out.data(), out.size()))) {
		std::printf("vector roundtrip: FAIL\n");
		return 1;
	}
	if (v2 != v) {
		std::printf("vector roundtrip: FAIL (mismatch)\n");
		return 1;
	}
	std::printf("vector roundtrip ok\n");

	// 4) parseJson 到 vector<int>（数组路径）
	std::string arr = "[10,20,30]";
	std::vector<int> va;
	if (!parser.parseJson(va, arr) || va.size() != 3 || va[0] != 10 || va[2] != 30) {
		std::printf("parseJson(vector): FAIL\n");
		return 1;
	}
	std::printf("parseJson(vector) ok\n");

	std::printf("ALL TESTS PASSED\n");
	return 0;
}