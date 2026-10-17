// Consumer test for libphonenumber 8.13.51.
// Exercises the real C++ API: Parse + IsValidNumber + Format (E164).
#include <iostream>
#include <string>

#include <phonenumbers/phonenumber.pb.h>
#include <phonenumbers/phonenumberutil.h>

int main() {
  using ::i18n::phonenumbers::PhoneNumber;
  using ::i18n::phonenumbers::PhoneNumberUtil;

  PhoneNumberUtil* util = PhoneNumberUtil::GetInstance();
  if (util == NULL) {
    std::cerr << "GetInstance returned null" << std::endl;
    return 1;
  }

  PhoneNumber num;
  if (util->Parse("6502530000", "US", &num) != PhoneNumberUtil::NO_PARSING_ERROR) {
    std::cerr << "Parse failed" << std::endl;
    return 1;
  }
  std::cout << "CHECK 1 parse OK" << std::endl;

  if (!util->IsValidNumber(num)) {
    std::cerr << "Number judged invalid" << std::endl;
    return 1;
  }
  std::cout << "CHECK 2 valid OK" << std::endl;

  std::string out;
  util->Format(num, PhoneNumberUtil::E164, &out);
  if (out != "+16502530000") {
    std::cerr << "Format mismatch: " << out << std::endl;
    return 1;
  }
  std::cout << "CHECK 3 format OK: " << out << std::endl;
  return 0;
}
