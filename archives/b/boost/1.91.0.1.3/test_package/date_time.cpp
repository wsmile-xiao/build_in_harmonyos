#include <string>

#include <boost/date_time/posix_time/posix_time.hpp>

int main() {
    const auto value = boost::posix_time::time_from_string(
        "2026-08-02 05:00:00");
    const std::string formatted =
        boost::posix_time::to_iso_extended_string(value);
    return !value.is_not_a_date_time() &&
                   formatted == "2026-08-02T05:00:00"
               ? 0
               : 1;
}
