#include <jthread/jthread.h>

#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>

class LifecycleThread : public jthread::JThread
{
public:
    std::atomic<int> executed{0};

    void *Thread() override
    {
        ThreadStarted();
        executed.store(1);
        return nullptr;
    }
};

int main()
{
    LifecycleThread worker;

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

    if (worker.executed.load() != 1)
    {
        std::cerr << "Thread body was not executed" << std::endl;
        return 3;
    }

    std::cout << "jthread lifecycle test passed" << std::endl;
    return 0;
}
