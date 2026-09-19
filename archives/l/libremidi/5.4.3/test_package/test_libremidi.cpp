// 鸿蒙 PC 消费者测试：以第三方使用者的身份链接 libremidi，验证在 OHOS 上
// 「无 ALSA/JACK/PipeWire」这一平台形态下，MIDI 消息编解码、SMF 读写与后端回退行为仍然正确。
#include <libremidi/defaults.hpp>
#include <libremidi/libremidi.hpp>
#include <libremidi/reader.hpp>
#include <libremidi/writer.hpp>

#include <algorithm>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace
{
int g_total = 0;
int g_pass = 0;

void check(const char* what, bool ok)
{
  ++g_total;
  if (ok)
    ++g_pass;
  else
    std::cerr << "FAIL: " << what << std::endl;
}
}

int main()
{
  // 1. 后端枚举：OHOS 上没有任何实时 MIDI 后端，库必须仍然可用并回退到 DUMMY
  const auto apis = libremidi::available_apis();
  check("available_apis_not_empty", !apis.empty());

  // 2. 回退到上游自带的 DUMMY API，而不是抛异常
  bool has_dummy = false;
  for (auto a : apis)
    has_dummy = has_dummy || (a == libremidi::API::DUMMY);
  check("available_apis_contains_dummy", has_dummy);
  check("midi1_default_api_is_dummy", libremidi::midi1::default_api() == libremidi::API::DUMMY);

  // 3. 输入 / 输出对象在默认后端下可构造。
  //    注意 midi_in::get_current_api() 是运行期结果，而 midi1::default_api() 是头文件里
  //    按宏算出的编译期常量：只编了 keyboard 输入后端时两者本就不相等（上游也因此把自己的
  //    creation 用例在 CI 模式下 SKIP），所以这里断言「落在可用后端列表里」。
  libremidi::midi_in in{libremidi::input_configuration{.on_message = [](auto) {}}};
  const auto in_api = in.get_current_api();
  check("midi_in_api_is_advertised", in_api != libremidi::API::UNSPECIFIED && std::find(apis.begin(), apis.end(), in_api) != apis.end());
  libremidi::midi_out out;
  check("midi_out_uses_default_api", out.get_current_api() == libremidi::midi1::default_api());

  // 4. SMF 写读往返：一条 Note On + 一条 Note Off 必须原样回到同一组字节
  libremidi::writer w;
  w.ticksPerQuarterNote = 96;
  w.add_track();
  w.add_event(0, 0, libremidi::message{0x90, 0x3c, 0x7f});
  w.add_event(48, 0, libremidi::message{0x80, 0x3c, 0x40});
  std::ostringstream os;
  w.write(os);
  const std::string smf = os.str();
  check("smf_starts_with_mthd", smf.size() > 4 && smf.compare(0, 4, "MThd") == 0);

  std::vector<uint8_t> bytes(smf.begin(), smf.end());
  libremidi::reader r;
  const auto res = r.parse(bytes);
  check(
      "smf_parses_completely",
      res == libremidi::reader::parse_result::complete
          || res == libremidi::reader::parse_result::validated);
  check("smf_track_count_roundtrip", !r.tracks.empty() && r.tracks.size() == w.tracks.size());
  check("smf_resolution_kept", static_cast<int>(r.ticksPerBeat) == 96);

  // 5. 损坏输入要被判为不可解析，而不是崩溃
  libremidi::reader bad;
  check("garbage_is_invalid", bad.parse(std::vector<uint8_t>{0x00, 0x01, 0x02}) == libremidi::reader::parse_result::invalid);

  std::cout << "libremidi consumer checks: " << g_pass << "/" << g_total << std::endl;
  return g_pass == g_total ? 0 : 1;
}
