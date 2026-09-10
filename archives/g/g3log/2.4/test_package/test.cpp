// test_package consumer test — actually exercises the g3log public API.
// Logs via g3log sinks and verifies the produced log file exists and
// contains the expected marker once the LogWorker is destroyed (the
// FileSink closes/flushes its ofstream only at destruction) (R34).
#include <g3log/g3log.hpp>
#include <g3log/logworker.hpp>
#include <g3log/filesink.hpp>

#include <atomic>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <memory>
#include <string>
#include <thread>

namespace {

// Minimal sink class following the upstream test pattern
// (see test_unit/test_sink.cpp ScopedSetTrue).
class FlushCounterSink {
    std::atomic<int>* counter;

  public:
    explicit FlushCounterSink(std::atomic<int>* c) : counter(c) {}
    void ReceiveMsg(g3::LogMessageMover) { counter->fetch_add(1); }
};

std::atomic<int> g_flushed{0};

}  // namespace

int main() {
    std::string log_path;
    {
        // Use the current (writable) working directory for the log file
        auto worker = g3::LogWorker::createLogWorker();
        auto handle = worker->addDefaultLogger("test_g3log", ".", "test_g3log");

        // Register the counting sink BEFORE logging so it observes the messages
        worker->addSink(std::make_unique<FlushCounterSink>(&g_flushed),
                        &FlushCounterSink::ReceiveMsg);
        g3::initializeLogging(worker.get());

        // Exercise core async logging API
        LOG(INFO) << "test_g3log consumer marker 42";
        LOG(WARNING) << "second consumer line";

        // Wait for the background logging threads to flush
        for (int i = 0; i < 50; ++i) {
            if (g_flushed.load() > 0) break;
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }

        // Query the real log file name from the default file sink
        if (handle) {
            auto future = handle->call(&g3::FileSink::fileName);
            log_path = future.get();
        }
        g3::internal::shutDownLogging();
        // worker (and FileSink) destroyed here -> log file flushed & closed
    }

    if (log_path.empty()) {
        std::fprintf(stderr, "FAIL: could not determine log file name\n");
        return 1;
    }

    bool ok = false;
    std::string content;
    for (int i = 0; i < 50; ++i) {
        std::ifstream log(log_path);
        if (log.good()) {
            content.assign(std::istreambuf_iterator<char>(log),
                           std::istreambuf_iterator<char>());
            if (content.find("consumer marker 42") != std::string::npos) {
                ok = true;
                break;
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    std::remove(log_path.c_str());
    if (!ok) {
        std::fprintf(stderr,
                     "FAIL: marker missing in log file: %s (content size=%zu)\n",
                     log_path.c_str(), content.size());
        return 1;
    }
    std::printf("PASS: g3log consumer test, log=%s size=%zu\n",
                log_path.c_str(), content.size());
    return 0;
}