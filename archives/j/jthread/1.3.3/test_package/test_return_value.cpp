#include <jthread/jthread.h>

#include <chrono>
#include <iostream>
#include <thread>

class ReturnValueThread : public jthread::JThread
{
public:
    void *Thread() override
    {
        ThreadStarted();
        return this;
    }
};
int main()
{
    ReturnValueThread worker;

    if (worker.Start() < 0)
    {
        std::cerr << "Start failed" << std::endl;
        return 1;
    }

    for (int i = 0; i < 1000 && worker.IsRunning(); ++i)
        std::this_thread::sleep_for(std::chrono::milliseconds(1));

    if (worker.IsRunning())
    {
        std::cerr << "Thread did not finish" << std::endl;
        return 2;
    }

    if (worker.GetReturnValue() != &worker)
    {
        std::cerr << "Unexpected thread return value" << std::endl;
        return 3;
    }

    std::cout << "jthread return value test passed" << std::endl;
    return 0;
}
