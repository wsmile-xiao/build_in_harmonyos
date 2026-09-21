// Consumer test: Arcus::Error value semantics.
// Covers default construction, code/message accessors, validity, fatal and
// native codes, string conversion and stream output. Exit 0 means all 6
// checks passed.
#include <Arcus/Error.h>

#include <cstdio>
#include <sstream>
#include <string>

int main()
{
    // 1. Default-constructed error is invalid.
    Arcus::Error empty;
    if (empty.isValid())
    {
        std::printf("FAIL 1: default Error should be invalid\n");
        return 1;
    }

    // 2. Code and message round-trip.
    Arcus::Error err(Arcus::ErrorCode::ConnectFailedError, "connect failed");
    if (err.getErrorCode() != Arcus::ErrorCode::ConnectFailedError)
    {
        std::printf("FAIL 2: error code did not round-trip\n");
        return 2;
    }
    if (err.getErrorMessage() != "connect failed")
    {
        std::printf("FAIL 3: error message did not round-trip\n");
        return 3;
    }

    // 3. Parametrized error is valid.
    if (!err.isValid())
    {
        std::printf("FAIL 4: parametrized Error should be valid\n");
        return 4;
    }

    // 4. Fatal flag and native code round-trip.
    err.setFatalError(true);
    err.setNativeErrorCode(111);
    if (!err.isFatalError() || err.getNativeErrorCode() != 111)
    {
        std::printf("FAIL 5: fatal flag or native code did not round-trip\n");
        return 5;
    }

    // 5. String conversion and stream output are non-empty.
    std::string text = err.toString();
    std::ostringstream stream;
    stream << err;
    if (text.empty() || stream.str().empty())
    {
        std::printf("FAIL 6: toString/stream output is empty\n");
        return 6;
    }

    std::printf("test_error OK: 6 error checks passed (%s)\n", text.c_str());
    return 0;
}
