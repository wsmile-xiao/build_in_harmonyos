#include <outcome.hpp>
#include <cstdio>
#include <string>

int main(){
  namespace o = OUTCOME_V2_NAMESPACE;
  int failures = 0;

  // 1) unchecked: narrow observers, value path
  o::unchecked<int, long> r = o::success(5);
  if (!(r.has_value() && r.value() == 5)) { printf("FAIL: unchecked value\n"); ++failures; }

  // 2) unchecked: error path
  o::unchecked<int, long> e = o::failure(long(77));
  if (!(e.has_error() && e.error() == 77)) { printf("FAIL: unchecked error\n"); ++failures; }

  // 3) checked: error() observer throws the E on value path is UB-free narrow here use has_error first
  o::checked<int, long> c = o::failure(long(88));
  if (!(c.has_error() && c.error() == 88)) { printf("FAIL: checked error\n"); ++failures; }

  // 4) checked value path
  o::checked<int, long> cv = o::success(9);
  if (!(cv.has_value() && cv.value() == 9)) { printf("FAIL: checked value\n"); ++failures; }

  // 5) string payload with checked
  o::checked<std::string, long> s = o::success(std::string("ok"));
  if (!(s.has_value() && s.value() == "ok")) { printf("FAIL: string payload\n"); ++failures; }

  if (failures == 0) {
    printf("PASS: single-header outcome unchecked/checked success/failure/observers\n");
    return 0;
  }
  return 1;
}
