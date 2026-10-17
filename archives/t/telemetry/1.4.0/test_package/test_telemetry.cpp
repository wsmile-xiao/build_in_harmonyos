/**
 * @file
 * @brief Consumer test of the packaged telemetry core library.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */

#include <telemetry.hpp>

#include <cstdint>
#include <cstdio>
#include <memory>
#include <string>
#include <variant>
#include <vector>

using namespace telemetry;

namespace {

int g_failures = 0;

#define CHECK(condition)                                                                           \
	do {                                                                                           \
		if (!(condition)) {                                                                        \
			std::fprintf(                                                                          \
				stderr, "CHECK failed: %s (%s:%d)\n", #condition, __FILE__, __LINE__);            \
			++g_failures;                                                                          \
		}                                                                                          \
	} while (false)

/**
 * @brief File operations, name resolution and disabling.
 */
void testFileOperations()
{
	int64_t counter = 0;

	FileOps ops {};
	ops.read = [&counter]() { return Content {Scalar {int64_t {++counter}}}; };
	ops.clear = [&counter]() { counter = 0; };

	auto root = Directory::create();
	CHECK(root->getFullPath() == "/");

	auto file = root->addFile("counter", ops);
	CHECK(file->hasRead());
	CHECK(file->hasClear());
	CHECK(file->getFullPath() == "/counter");
	CHECK(file->read() == Content {Scalar {int64_t {1}}});
	CHECK(file->read() == Content {Scalar {int64_t {2}}});

	file->clear();
	CHECK(file->read() == Content {Scalar {int64_t {1}}});

	file->disable();
	CHECK(!file->hasRead());
	CHECK(!file->hasClear());
}

/**
 * @brief Tree navigation, entry lookup and symbolic links.
 */
void testTreeEntriesAndSymlink()
{
	auto root = Directory::create();
	auto subDir = root->addDirs("group/sub");

	FileOps ops {};
	ops.read = []() { return Content {Scalar {std::string {"hello"}}}; };
	auto file = subDir->addFile("greeting", ops);

	CHECK(subDir->getFullPath() == "/group/sub");
	CHECK(file->getFullPath() == "/group/sub/greeting");

	auto link = root->addSymlink("link", file);
	CHECK(link->getTarget() == file);
	CHECK(root->getEntry("link") == link);
	CHECK(subDir->getEntry("greeting") == file);

	const std::vector<std::string> entries = root->listEntries();
	CHECK(entries.size() == 2);
}

/**
 * @brief Aggregation of multiple files into a single aggregated file.
 */
void testAggregatedFile()
{
	auto root = Directory::create();
	auto dir = root->addDir("ports");

	// A directory only keeps weak pointers to its entries: keep the returned
	// pointers alive, otherwise the files disappear before the aggregation.
	std::vector<std::shared_ptr<File>> files;

	const uint64_t packets[] = {1, 4, 10};
	for (uint64_t value : packets) {
		FileOps ops {};
		ops.read = [value]() { return Dict({{"packets", Scalar {value}}}); };
		files.push_back(dir->addFile("port" + std::to_string(value), ops));
	}
	CHECK(files.size() == 3);

	const AggOperation sumOp {AggMethodType::SUM, "packets", "sumPackets"};
	const AggOperation avgOp {AggMethodType::AVG, "packets", "avgPackets"};
	auto aggFile = root->addAggFile("summary", R"(ports/port\d+)", {sumOp, avgOp});

	const Content content = aggFile->read();
	CHECK(std::holds_alternative<Dict>(content));
	if (std::holds_alternative<Dict>(content)) {
		const Dict& dict = std::get<Dict>(content);
		CHECK(dict.size() == 2);
		CHECK(std::get<uint64_t>(std::get<Scalar>(dict.at("sumPackets"))) == 15);
		CHECK(std::get<double>(std::get<Scalar>(dict.at("avgPackets"))) == 5.0);
	}
}

/**
 * @brief Dictionary formatting through the public content helper.
 */
void testContentToString()
{
	FileOps ops {};
	ops.read = []() {
		Dict dict {};
		dict.emplace("key", DictValue {Scalar {std::string {"value"}}});
		return dict;
	};

	auto root = Directory::create();
	auto file = root->addFile("dict", ops);

	const std::string text = contentToString(file->read());
	CHECK(!text.empty());
	CHECK(text.find("key") != std::string::npos);
	CHECK(text.find("value") != std::string::npos);
}

} // namespace

int main()
{
	testFileOperations();
	testTreeEntriesAndSymlink();
	testAggregatedFile();
	testContentToString();

	if (g_failures != 0) {
		std::fprintf(stderr, "test_telemetry_consumer: %d check(s) failed\n", g_failures);
		return 1;
	}

	std::puts("test_telemetry_consumer: telemetry core API checks passed");
	return 0;
}
