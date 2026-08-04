#include "eventpp/callbacklist.h"
#include "eventpp/eventdispatcher.h"
#include "eventpp/eventqueue.h"

#include <string>
#include <iostream>
#include <cstdlib>

int main() {
    // Test CallbackList
    {
        eventpp::CallbackList<void(const std::string &, const bool)> callbackList;
        int callCount = 0;
        callbackList.append([&callCount](const std::string & s, const bool b) {
            if (s != "Hello") return 1;
            if (b != true) return 1;
            ++callCount;
            return 0;
        });
        callbackList("Hello", true);
        if (callCount != 1) return 1;
    }

    // Test EventDispatcher
    {
        eventpp::EventDispatcher<int, void()> dispatcher;
        int event3Count = 0;
        int event5Count = 0;
        dispatcher.appendListener(3, [&event3Count]() { ++event3Count; });
        dispatcher.appendListener(5, [&event5Count]() { ++event5Count; });
        dispatcher.appendListener(5, [&event5Count]() { ++event5Count; });
        dispatcher.dispatch(3);
        dispatcher.dispatch(5);
        if (event3Count != 1) return 1;
        if (event5Count != 2) return 1;
    }

    // Test EventQueue
    {
        eventpp::EventQueue<int, void(const std::string &)> queue;
        std::string received;
        queue.appendListener(5, [&received](const std::string & s) { received = s; });
        queue.enqueue(5, "World");
        if (!received.empty()) return 1;
        queue.process();
        if (received != "World") return 1;
    }

    std::cout << "All eventpp tests passed!" << std::endl;
    return 0;
}
