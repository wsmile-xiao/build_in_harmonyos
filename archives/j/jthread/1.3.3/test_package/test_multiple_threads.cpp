#include <jthread/jthread.h>

#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>

class CountingThread : public jthread::JThread
{
public:
    explicit CountingThread(std::atomic<int> &counter)
        : counter_(counter)
    {
    }

    void *Thread() override
    {
        ThreadStarted();
        counter_.fetch_add(1);
        return nullptr;
    }

private:
    std::atomic<int> &counter_;
};
int main()
{
    std::atomic<int> counter{0};

    CountingThread worker1(counter);
    CountingThread worker2(counter);
    CountingThread worker3(counter);

    if (worker1.Start() < 0 || worker2.Start() < 0 || worker3.Start() < 0)
    {
        std::cerr << "Failed to start one or more threads" << std::endl;
        return 1;
    }

    for (int i = 0; i < 1000; ++i)
    {
        if (!worker1.IsRunning() && !worker2.IsRunning() && !worker3.IsRunning())
            break;
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }

    if (worker1.IsRunning() || worker2.IsRunning() || worker3.IsRunning())
    {
        std::cerr << "One or more threads did not finish" << std::endl;
        return 2;
    }

    if (counter.load() != 3)
    {
        std::cerr << "Expected 3 thread executions, got " << counter.load() << std::endl;
        return 3;
    }

    std::cout << "jthread multiple threads test passed" << std::endl;
    return 0;
}
