#include <bitserializer/convert.h>
#include <string>
#include <stdexcept>
#include <type_traits>

int main()
{
	using namespace BitSerializer;

	// Exercise the header-only core API: string <-> numeric conversions.
	const std::string intStr = Convert::To<std::string>(42);
	if (intStr != "42") {
		throw std::runtime_error("To<std::string>(42) failed");
	}
	const int intVal = Convert::To<int>("42");
	if (intVal != 42) {
		throw std::runtime_error("To<int>(\"42\") failed");
	}

	const std::string floatStr = Convert::To<std::string>(3.5);
	const double floatVal = Convert::To<double>(floatStr);
	if (floatVal != 3.5) {
		throw std::runtime_error("float round-trip failed");
	}

	return 0;
}
