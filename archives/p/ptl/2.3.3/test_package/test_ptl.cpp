#include <PTL/PTL.hh>
#include <PTL/Threading.hh>
#include <PTL/Version.hh>

#include <atomic>
#include <cstdlib>
#include <iostream>
#include <string>

namespace
{
int passed = 0;

void check(bool condition, const char* name)
{
    if(!condition)
    {
        std::cerr << "FAIL: " << name << std::endl;
        std::exit(EXIT_FAILURE);
    }
    ++passed;
    std::cout << "PASS: " << name << std::endl;
}
}  // namespace

int main()
{
    check(std::string{ PTL_VERSION_STRING } == "2.3.3", "version metadata");

    PTL::TaskRunManager manager{ false };
    manager.Initialize(2);
    check(manager.IsInitialized(), "task run manager initialization");
    check(manager.GetNumberOfThreads() == 2, "requested native worker count");

    auto* task_manager = manager.GetTaskManager();
    auto  future       = task_manager->async<int>([]() { return 6 * 7; });
    check(future->get() == 42, "asynchronous task result");

    auto join = [](int& result, int&& value) { return result += value; };
    PTL::TaskGroup<int> squares{ join, manager.GetThreadPool() };
    for(int value = 1; value <= 4; ++value)
        squares.exec([](int input) { return input * input; }, value);
    check(squares.join() == 30, "task group reduction");

    std::atomic<int> void_counter{ 0 };
    PTL::TaskGroup<void> void_group{ manager.GetThreadPool() };
    for(int i = 0; i < 5; ++i)
        void_group.exec([&void_counter]() { ++void_counter; });
    void_group.join();
    check(void_counter.load() == 5, "void task group completion");

#if defined(__OHOS__)
    check(PTL::Threading::GetNumberOfCores() > 0,
          "HarmonyOS CPU topology through PTL threading API");
#else
#    error "This consumer test must be compiled for HarmonyOS"
#endif

    manager.Terminate();
    std::cout << "PTL consumer assertions: " << passed << "/7" << std::endl;
    return (passed == 7) ? EXIT_SUCCESS : EXIT_FAILURE;
}
