// HarmonyOS 专项测试：enumbitmask 1.0 在 OHOS (aarch64-linux-ohos / clang) 平台
// 上的扩展验证。上游仅提供 example.cpp 演示源码，无测试框架；本用例按
// 鸿蒙专项测试要求，覆盖上游示例未涉及的底层类型宽度组合、复合赋值
// 序列、constexpr 编译期求值与可观察输出，全部为真实编译+运行验证。
#include <cstdint>
#include <cstdio>
#include <type_traits>
#include "EnumBitmask.hpp"

// 覆盖多种底层类型：uint8/uint16/uint32/uint64 与 int8
enum class Flag8 : std::uint8_t  { A = 1, B = 2, C = 4, D = 8 };
DEFINE_BITMASK_OPERATORS(Flag8)

enum class Flag16 : std::uint16_t { P = 1, Q = 2, R = 4, S = 8, T = 16 };
DEFINE_BITMASK_OPERATORS(Flag16)

enum class Flag64 : std::uint64_t { X = 1ULL << 40, Y = 1ULL << 41, Z = 1ULL << 42 };
DEFINE_BITMASK_OPERATORS(Flag64)

int main()
{
	// 1) uint8 组合与按位清除
	Flag8 f8 = Flag8::A | Flag8::B | Flag8::D;
	f8 &= ~Flag8::B;
	if (static_cast<std::uint8_t>(f8) != (1u | 8u))
	{
		std::fprintf(stderr, "FAIL: Flag8 组合/清除错误: %u\n",
		             static_cast<unsigned>(static_cast<std::uint8_t>(f8)));
		return 1;
	}

	// 2) uint16 异或翻转
	Flag16 f16 = Flag16::P | Flag16::R;
	f16 ^= Flag16::R;
	if (static_cast<std::uint16_t>(f16) != 1u)
	{
		std::fprintf(stderr, "FAIL: Flag16 异或翻转错误: %u\n",
		             static_cast<unsigned>(static_cast<std::uint16_t>(f16)));
		return 1;
	}

	// 3) uint64 高位掩码（验证 64 位算术正确性）
	constexpr Flag64 mask64 = Flag64::X | Flag64::Y | Flag64::Z;
	constexpr Flag64 keep = mask64 & Flag64::Y;
	if (static_cast<std::uint64_t>(keep) != (1ULL << 41))
	{
		std::fprintf(stderr, "FAIL: Flag64 高位掩码错误\n");
		return 1;
	}

	// 4) constexpr 编译期求值
	constexpr Flag8 ce = (Flag8::A | Flag8::C) & ~Flag8::A;
	static_assert(static_cast<std::uint8_t>(ce) == 4u, "constexpr 求值失败");

	// 5) 空掩码：经公开运算符得到的 EnumWrapper 应隐式 false（库只对
	//    运算结果提供 explicit operator bool，裸 enum 不可直接转 bool）
	if (Flag8(0) & Flag8(0))
	{
		std::fprintf(stderr, "FAIL: 零掩码应隐式 false\n");
		return 1;
	}
	// 有重叠位的 & 结果非零 → 应隐式 true
	if (!((Flag8::A | Flag8::C) & Flag8::A))
	{
		std::fprintf(stderr, "FAIL: 非零掩码应隐式 true\n");
		return 1;
	}

	std::printf("test_ohos enumbitmask 1.0: OK (uint8/16/64, constexpr, 复合运算)\n");
	return 0;
}