// test_json_dto.cpp — json_dto 0.3.4 consumer round-trip test.
//
// Exercises the real public API: struct -> to_json -> from_json with
// mandatory/optional (json_dto::cpp17::optional) fields, plus a top-level
// array of structs. Exits non-zero on any failed check (16 explicit checks).
#include <json_dto/pub.hpp>

#include <string>
#include <vector>
#include <cstdlib>
#include <iostream>

struct message_t {
	std::string from;
	std::string to;
	int m_type{0};
	json_dto::cpp17::optional<int> extra;
};

namespace json_dto {

template<typename Json_Io>
void json_io(Json_Io & io, message_t & m) {
	io & mandatory("from", m.from)
	   & mandatory("to", m.to)
	   & mandatory("type", m.m_type)
	   & optional("extra", m.extra, json_dto::cpp17::nullopt());
}

} /* namespace json_dto */

static int checks = 0;

static void check(bool cond, const char * what) {
	++checks;
	if (!cond) {
		std::cerr << "FAILED: " << what << std::endl;
		std::exit(1);
	}
}

int main() {
	// 1) Basic round-trip with mandatory fields, absent optional.
	const message_t msg{"alice", "bob", 7, json_dto::cpp17::nullopt()};
	const std::string json = json_dto::to_json(msg);
	check(json.find("\"from\":\"alice\"") != std::string::npos, "to_json from field");
	check(json.find("\"to\":\"bob\"") != std::string::npos, "to_json to field");
	check(json.find("\"type\":7") != std::string::npos, "to_json type field");
	check(json.find("extra") == std::string::npos, "absent optional omitted");

	const message_t parsed = json_dto::from_json<message_t>(json);
	check(parsed.from == "alice", "from_json from");
	check(parsed.to == "bob", "from_json to");
	check(parsed.m_type == 7, "from_json type");
	check(!parsed.extra.has_value(), "from_json absent optional");

	// 2) Optional field present.
	const message_t msg2{"carol", "dave", 1, json_dto::cpp17::optional<int>{42}};
	const std::string json2 = json_dto::to_json(msg2);
	check(json2.find("\"extra\":42") != std::string::npos, "present optional serialized");
	const message_t parsed2 = json_dto::from_json<message_t>(json2);
	check(parsed2.extra.has_value() && *parsed2.extra == 42, "present optional parsed");

	// 3) From JSON with an extra unknown member.
	const message_t parsed3 = json_dto::from_json<message_t>(
			R"({"from":"eve","to":"frank","type":3,"unknown":"ignored"})");
	check(parsed3.from == "eve" && parsed3.to == "frank" && parsed3.m_type == 3,
			"unknown member tolerated");

	// 4) Validators reject a type mismatch.
	bool rejected = false;
	try {
		json_dto::from_json<message_t>(R"({"from":"x","to":"y","type":"NaN"})");
	} catch (const std::exception &) {
		rejected = true;
	}
	check(rejected, "type mismatch rejected by validator");

	// 5) Top-level array of structs.
	const std::vector<message_t> msgs{
		{"a1", "b1", 1, json_dto::cpp17::nullopt()},
		{"a2", "b2", 2, json_dto::cpp17::optional<int>{99}},
	};
	const std::string arr = json_dto::to_json(msgs);
	check(arr.find("\"from\":\"a1\"") != std::string::npos, "array serialize first");
	check(arr.find("\"from\":\"a2\"") != std::string::npos, "array serialize second");
	const auto parsed_arr = json_dto::from_json<std::vector<message_t>>(arr);
	check(parsed_arr.size() == 2, "array parse size");
	check(parsed_arr[1].extra.has_value() && *parsed_arr[1].extra == 99, "array element optional");

	if (checks != 16) {
		std::cerr << "FAILED: expected 16 checks, saw " << checks << std::endl;
		return 1;
	}
	std::cout << "json_dto round-trip OK (" << checks << " checks)" << std::endl;
	return 0;
}