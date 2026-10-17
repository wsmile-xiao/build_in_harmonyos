// test_package consumer test for hippomocks 5.0 (header-only).
// Uses ONLY the public API of the installed package (MockRepository,
// Mock<T>, ExpectCall, Return, With, VerifyAndClear) through <hippomocks.h>.
#include <hippomocks.h>

#include <cstdio>
#include <cstring>

// A business-style component interface (simulates an upstream caller).
class ILogger {
public:
    virtual ~ILogger() {}
    virtual int log(const char* msg) = 0;
};

class ICalculator {
public:
    virtual ~ICalculator() {}
    virtual int add(int a, int b) = 0;
    virtual int multiply(int a, int b) = 0;
};

int main() {
    MockRepository mocks;
    ILogger* logger = mocks.Mock<ILogger>();
    ICalculator* calc = mocks.Mock<ICalculator>();

    mocks.ExpectCall(logger, ILogger::log).With("hello").Return(1);
    mocks.ExpectCall(calc, ICalculator::add).With(2, 3).Return(5);
    mocks.ExpectCall(calc, ICalculator::multiply).With(4, 4).Return(16);

    int logged = logger->log("hello");
    int sum = calc->add(2, 3);
    int prod = calc->multiply(4, 4);

    bool ok = (logged == 1) && (sum == 5) && (prod == 16);
    printf("consumer: log()=%d add()=%d multiply()=%d -> %s\n",
           logged, sum, prod, ok ? "PASS" : "FAIL");

    mocks.VerifyAll();
    return ok ? 0 : 1;
}