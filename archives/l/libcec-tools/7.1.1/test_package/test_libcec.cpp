#include <libcec/cec.h>

#include <array>
#include <cstdio>
#include <cstdlib>
#include <initializer_list>
#include <string>

int main(int argc, char** argv)
{
  if (argc != 2)
  {
    std::fprintf(stderr, "usage: test_libcec <installed-cec-client>\n");
    return 1;
  }

  CEC::libcec_configuration config;
  CEC::ICECAdapter* adapter = CECInitialise(&config);
  if (adapter == nullptr)
  {
    std::fprintf(stderr, "CECInitialise returned null\n");
    return 2;
  }

  const uint32_t expected = LIBCEC_VERSION_TO_UINT(7, 1, 1);
  if (config.serverVersion != expected)
  {
    std::fprintf(stderr, "unexpected libCEC server version: 0x%08x\n",
                 config.serverVersion);
    CECDestroy(adapter);
    return 3;
  }

  CECDestroy(adapter);

  // Exercise the installed command-line consumer against real CLI input and
  // verify the help output emitted by the packaged libCEC tool. This remains
  // hardware-independent while testing executable loading and dispatch.
  const std::string command = std::string("\"") + argv[1] +
                              "\" --help 2>&1";
  FILE* child = popen(command.c_str(), "r");
  if (child == nullptr)
  {
    std::perror("popen cec-client --help");
    return 4;
  }

  std::string output;
  std::array<char, 512> buffer{};
  while (std::fgets(buffer.data(), static_cast<int>(buffer.size()), child))
    output += buffer.data();
  const int status = pclose(child);
  if (status != 0)
  {
    std::fprintf(stderr, "installed cec-client --help exited with status %d\n",
                 status);
    return 5;
  }

  for (const char* expected : {"parameters:", "--list-devices",
                               "Shows this help text"})
  {
    if (output.find(expected) == std::string::npos)
    {
      std::fprintf(stderr, "cec-client --help output missing: %s\n", expected);
      return 6;
    }
  }

  std::puts("libcec 7.1.1 API consumer test passed");
  std::puts("installed cec-client --help end-to-end test passed (3 output checks)");
  return 0;
}
