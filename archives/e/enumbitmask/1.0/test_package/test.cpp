// test_package: 消费者视角验证 enumbitmask 1.0
// 仅通过公开头文件 <EnumBitmask.hpp> 与公开宏 DEFINE_BITMASK_OPERATORS
// 使用该库，模拟业务上层组件（文件打开模式标志）的典型用法，
// 验证第三方使用者可以编译、链接并实际运行位掩码运算。
#include <cstdint>
#include <cstdio>
#include <type_traits>
#include "EnumBitmask.hpp"

// 业务场景：文件打开模式（仿 <fstream> openmode 语义）
enum class OpenMode : std::uint32_t
{
	Append	= 1,
	Binary	= 2,
	Input	= 4,
	Output	= 8,
};
DEFINE_BITMASK_OPERATORS(OpenMode)

// 业务场景：权限位（低 4 位掩码）
enum class Perm : std::uint8_t
{
	None	= 0,
	Read	= 1,
	Write	= 2,
	Exec	= 4,
};
DEFINE_BITMASK_OPERATORS(Perm)

int main()
{
	// 组合标志：Binary | Input（公开运算符 |）
	constexpr OpenMode mode = OpenMode::Binary | OpenMode::Input;
	static_assert(mode == OpenMode(6), "| 组合结果应为 2|4=6");

	// 检查位（公开运算符 & 与 bool 转换）
	if (!(mode & OpenMode::Binary))
	{
		std::fprintf(stderr, "FAIL: Binary 位未置位\n");
		return 1;
	}
	if (mode & OpenMode::Output)
	{
		std::fprintf(stderr, "FAIL: Output 位不应置位\n");
		return 1;
	}

	// 取反（公开运算符 ~）
	constexpr OpenMode all = ~OpenMode(0);
	static_assert(all == OpenMode(~std::uint32_t(0)), "~ 结果错误");

	// 异或（公开运算符 ^）
	constexpr OpenMode x = OpenMode::Input ^ OpenMode::Output;
	static_assert(x == OpenMode(12), "^ 结果应为 4^8=12");

	// 复合赋值（公开运算符 |= / &= / ^=）
	OpenMode m = OpenMode::Append;
	m |= OpenMode::Output;
	if (!(m & OpenMode::Output))
	{
		std::fprintf(stderr, "FAIL: |= 后 Output 未置位\n");
		return 1;
	}
	m &= OpenMode::Append;
	if (m & OpenMode::Output)
	{
		std::fprintf(stderr, "FAIL: &= 后 Output 应被清除\n");
		return 1;
	}
	m ^= OpenMode::Append;
	if (m & OpenMode::Append)
	{
		std::fprintf(stderr, "FAIL: ^= 后 Append 应被翻转清除\n");
		return 1;
	}

	// 第二个枚举类型（不同底层类型 std::uint8_t），验证宏可复用
	constexpr Perm p = Perm::Read | Perm::Exec;
	static_assert(p == Perm(5), "Perm | 结果应为 1|4=5");
	if (!(p & Perm::Read))
	{
		std::fprintf(stderr, "FAIL: Perm Read 位未置位\n");
		return 1;
	}

	// 可观察结果输出
	std::printf("test enumbitmask 1.0: OK (mode=%u, perm=%u)\n",
	            static_cast<unsigned>(static_cast<std::uint32_t>(mode)),
	            static_cast<unsigned>(static_cast<std::uint8_t>(p)));
	return 0;
}
