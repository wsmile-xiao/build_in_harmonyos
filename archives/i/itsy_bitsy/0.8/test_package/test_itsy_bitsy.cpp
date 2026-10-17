// Consumer test for the header-only itsy_bitsy/0.8 Conan package.
//
// Each case is registered as its own CTest entry so that a failure names the
// behaviour that broke.  Every case really calls into <itsy/...> headers: the
// `bit_span` case additionally proves that the declared public dependency
// span-lite reaches consumers, because itsy/detail/span.hpp emits
// "#error a span of some sort is required" without a span implementation.

#include <itsy/bitsy.hpp>

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

// Compile-time expectation: removed or changed by the negative run recorded in
// notes.md, which makes the consumer target fail to compile.
static_assert(bitsy::binary_digits_v<unsigned char> == 8,
	"itsy.bitsy must expose the binary digit constants");

namespace
{

void
	report_failure(const char* expression, int line)
	{
		std::fprintf(stderr, "FAIL: %s (line %d)\n", expression, line);
	}

#define CHECK_EXPR(expression) \
	do                       \
	{                        \
		if (!(expression))   \
		{                    \
			report_failure(#expression, __LINE__); \
			return 1;        \
		}                    \
	} while (0)

	int
	test_binary_digits()
	{
		CHECK_EXPR(bitsy::binary_digits_v<unsigned char> == 8);
		CHECK_EXPR(bitsy::binary_digits_v<unsigned short> == 16);
		CHECK_EXPR(bitsy::binary_digits_v<unsigned int> == 32);
		CHECK_EXPR(bitsy::binary_digits_v<std::uint64_t> == 64);
		return 0;
	}

	int
	test_bit_vector()
	{
		bitsy::bit_vector<unsigned char> bits(8, false);
		bits[1] = true;
		bits[6] = true;
		CHECK_EXPR(bits.size() == 8);
		CHECK_EXPR(bits.count(true) == 2);
		CHECK_EXPR(bits.count(false) == 6);
		CHECK_EXPR(static_cast<bool>(bits[1]));
		CHECK_EXPR(!static_cast<bool>(bits[0]));
		return 0;
	}

	int
	test_bit_vector_flip()
	{
		bitsy::bit_vector<unsigned char> bits(8, false);
		bits[2] = true;
		CHECK_EXPR(bits.count(true) == 1);
		bits.flip(2);
		CHECK_EXPR(!static_cast<bool>(bits[2]));
		CHECK_EXPR(bits.count(true) == 0);
		bits.flip(3);
		CHECK_EXPR(static_cast<bool>(bits[3]));
		CHECK_EXPR(bits.count(true) == 1);
		return 0;
	}

	int
	test_popcount()
	{
		CHECK_EXPR(bitsy::popcount(static_cast<unsigned char>(0x00)) == 0);
		CHECK_EXPR(bitsy::popcount(static_cast<unsigned char>(0x81)) == 2);
		CHECK_EXPR(bitsy::popcount(static_cast<unsigned char>(0xF0)) == 4);
		CHECK_EXPR(bitsy::popcount(static_cast<unsigned char>(0xFF)) == 8);
		return 0;
	}

	// Exercises itsy/bit_span.hpp -> itsy/detail/span.hpp -> nonstd::span.hpp,
	// i.e. the span-lite Conan dependency, and that writes through the view
	// land in the caller's storage.
	int
	test_bit_span()
	{
		unsigned char storage[2] = { 0x00, 0x00 };
		bitsy::bit_span<unsigned char> bits(&storage[0], &storage[0] + 2);

		CHECK_EXPR(bits.size() == 16);
		CHECK_EXPR(bits.one_count() == 0);
		CHECK_EXPR(bits.zero_count() == 16);

		bits[0] = true;
		bits[15] = true;
		CHECK_EXPR(storage[0] == 0x01);
		CHECK_EXPR(storage[1] == 0x80);
		CHECK_EXPR(bits.one_count() == 2);
		CHECK_EXPR(bits.zero_count() == 14);

		bits[0] = false;
		CHECK_EXPR(storage[0] == 0x00);
		CHECK_EXPR(bits.one_count() == 1);
		return 0;
	}

	struct case_entry
	{
		const char* name;
		int (*run)();
	};

	const case_entry cases[] = {
		{ "binary_digits", test_binary_digits },
		{ "bit_vector", test_bit_vector },
		{ "bit_vector_flip", test_bit_vector_flip },
		{ "popcount", test_popcount },
		{ "bit_span", test_bit_span },
	};

} // namespace

int
main(int argc, char* argv[])
{
	const char* requested = (argc > 1) ? argv[1] : nullptr;

	if (requested != nullptr && std::strcmp(requested, "--list") == 0)
	{
		for (const case_entry& entry : cases)
		{
			std::printf("%s\n", entry.name);
		}
		return 0;
	}

	bool matched = false;
	for (const case_entry& entry : cases)
	{
		if (requested != nullptr && std::strcmp(requested, entry.name) != 0)
		{
			continue;
		}
		matched = true;
		if (entry.run() != 0)
		{
			std::fprintf(stderr, "case %s: FAILED\n", entry.name);
			return 1;
		}
		std::printf("PASS: %s\n", entry.name);
	}
	if (requested != nullptr && !matched)
	{
		std::fprintf(stderr, "unknown case: %s\n", requested);
		return 1;
	}
	return 0;
}
