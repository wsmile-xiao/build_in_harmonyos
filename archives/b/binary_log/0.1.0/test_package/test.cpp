#include <binary_log/binary_log.hpp>

#include <cstdint>
#include <filesystem>

int main()
{
  constexpr auto log_file = "binary_log_consumer.log";
  constexpr auto index_file = "binary_log_consumer.log.index";
  constexpr auto runlength_file = "binary_log_consumer.log.runlength";

  {
    binary_log::binary_log log(log_file);
    BINARY_LOG(log, "consumer value={}", std::int32_t {42});
  }

  const bool files_exist = std::filesystem::exists(log_file)
      && std::filesystem::exists(index_file)
      && std::filesystem::exists(runlength_file);
  const bool files_have_data = files_exist
      && std::filesystem::file_size(log_file) > 0
      && std::filesystem::file_size(index_file) > 0;

  std::filesystem::remove(log_file);
  std::filesystem::remove(index_file);
  std::filesystem::remove(runlength_file);
  return files_exist && files_have_data ? 0 : 1;
}
