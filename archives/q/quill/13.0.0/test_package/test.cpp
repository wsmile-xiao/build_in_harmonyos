#include <quill/Backend.h>
#include <quill/Frontend.h>
#include <quill/LogMacros.h>
#include <quill/sinks/ConsoleSink.h>
#include <quill/std/Vector.h>

#include <cstdio>
#include <string>
#include <vector>

int main()
{
  // Start the logging backend worker thread.
  quill::BackendOptions backend_options;
  quill::Backend::start(backend_options);

  // Create a console sink and a logger that uses it.
  auto console_sink = quill::Frontend::create_or_get_sink<quill::ConsoleSink>("sink_id_1");
  quill::Logger* logger = quill::Frontend::create_or_get_logger("root", std::move(console_sink));

  // Exercise the core formatting / logging path with several argument types.
  logger->set_log_level(quill::LogLevel::TraceL3);

  LOG_INFO(logger, "quill consumer test: int={} double={} str={}", 42, 3.14159, std::string{"hello"});
  LOG_WARNING(logger, "warning path: vector={}", std::vector<int>{1, 2, 3});
  LOG_TRACE_L3(logger, "trace path: {} {}", true, 'c');

  // Wait for all log records to be flushed to the sink.
  quill::Backend::stop();
  std::printf("test_quill: quill logging pipeline executed OK\n");
  return 0;
}