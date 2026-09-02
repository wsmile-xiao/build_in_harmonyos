// HarmonyOS/OHOS 专项测试：
// 验证 quill 在 OHOS 平台（/tmp 只读，E002）下能通过可写临时目录（$TMPDIR）写日志文件。
// 覆盖本次适配核心点：FileSink 使用可写临时目录，而非只读的 /tmp。
#include <quill/Backend.h>
#include <quill/Frontend.h>
#include <quill/LogMacros.h>
#include <quill/sinks/FileSink.h>

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

namespace
{
std::string writable_log_dir()
{
  // R10: 临时文件必须经 $TMPDIR（或 $HOME/tmp）；OHOS /tmp 只读（E002）。
  char const* tmp = std::getenv("TMPDIR");
  if (tmp != nullptr && *tmp != '\0')
  {
    return std::string{tmp};
  }
#if defined(__OHOS__)
  // OHOS 上 /tmp 只读：运行环境未注入 TMPDIR 时，回退到可写的用户临时目录。
  char const* home = std::getenv("HOME");
  return (home != nullptr && *home != '\0') ? std::string{home} + "/tmp" : std::string{"./tmp"};
#else
  // 非 OHOS 平台 /tmp 可写。
  return std::string{"/tmp"};
#endif
}
} // namespace

int main()
{
  std::string const log_path = writable_log_dir() + "/quill_ohos_test.log";

  quill::BackendOptions backend_options;
  quill::Backend::start(backend_options);

  auto file_sink = quill::Frontend::create_or_get_sink<quill::FileSink>(
    log_path,
    []()
    {
      quill::FileSinkConfig cfg;
      cfg.set_open_mode('w');
      return cfg;
    }(),
    quill::FileEventNotifier{});

  quill::Logger* logger = quill::Frontend::create_or_get_logger("ohos_test", std::move(file_sink));
  LOG_INFO(logger, "OHOS log path probe: {}", log_path);
  quill::Backend::stop();

  // 验证日志文件真实存在且包含内容（伪造输出=禁止，必须读回验证）
  std::ifstream in(log_path);
  if (!in.is_open())
  {
    std::printf("test_quill_ohos: FAIL - log file not created: %s\n", log_path.c_str());
    return 1;
  }
  std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
  if (content.find("OHOS log path probe") == std::string::npos)
  {
    std::printf("test_quill_ohos: FAIL - expected marker missing in %s\n", log_path.c_str());
    return 2;
  }
  std::printf("test_quill_ohos: PASS - log written to %s\n", log_path.c_str());
  return 0;
}
