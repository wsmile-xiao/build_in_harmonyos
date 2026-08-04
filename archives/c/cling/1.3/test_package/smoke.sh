#!/usr/bin/env bash
# Project-rule exception: test_package invokes Bash explicitly because this
# matrix requires pipefail, [[...]], and local variables.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: smoke.sh <cling>" >&2
  exit 2
fi

cling="$1"
total=0
failures=0

run_case() {
  local case_id="$1"
  local capability="$2"
  local expected="$3"
  local output
  local status
  shift 3

  total=$((total + 1))
  if output=$("$cling" -std=c++17 "$@" 2>&1); then
    status=0
  else
    status=$?
  fi

  if [[ $status -eq 0 ]] && printf '%s\n' "$output" | grep -Fx -- "$expected" >/dev/null; then
    printf '[pass] %s %s\n' "$case_id" "$capability"
    return
  fi

  failures=$((failures + 1))
  printf '[fail] %s %s exit=%s expected=%s\n' \
    "$case_id" "$capability" "$status" "$expected" >&2
  printf '%s\n' "$output" | sed -n '1,80p' >&2
}

run_case 001 vector_at_size CLING_CASE_001=12 \
  '#include <iostream>' \
  '#include <vector>' \
  'std::vector<int> values{4, 9, 16}; std::cout << "CLING_CASE_001=" << values.at(1) + static_cast<int>(values.size()) << std::endl;'

run_case 002 array_fill CLING_CASE_002=6 \
  '#include <array>' \
  '#include <iostream>' \
  'std::array<int, 4> values{}; values.fill(3); std::cout << "CLING_CASE_002=" << values.front() + values.back() << std::endl;'

run_case 003 deque_ends CLING_CASE_003=10 \
  '#include <deque>' \
  '#include <iostream>' \
  'std::deque<int> values{5}; values.push_front(2); values.push_back(8); std::cout << "CLING_CASE_003=" << values.front() + values.back() << std::endl;'

run_case 004 list_sort CLING_CASE_004=19 \
  '#include <iostream>' \
  '#include <list>' \
  'std::list<int> values{9, 1, 4}; values.sort(); std::cout << "CLING_CASE_004=" << values.front() * 10 + values.back() << std::endl;'

run_case 005 forward_list_remove CLING_CASE_005=3 \
  '#include <forward_list>' \
  '#include <iostream>' \
  '#include <iterator>' \
  'std::forward_list<int> values{1, 2, 3, 2, 4}; values.remove(2); std::cout << "CLING_CASE_005=" << std::distance(values.begin(), values.end()) << std::endl;'

run_case 006 set_unique_insert CLING_CASE_006=3 \
  '#include <iostream>' \
  '#include <set>' \
  'std::set<int> values{7, 2, 7, 5}; std::cout << "CLING_CASE_006=" << values.size() << std::endl;'

run_case 007 multiset_count CLING_CASE_007=3 \
  '#include <iostream>' \
  '#include <set>' \
  'std::multiset<int> values{4, 1, 4, 4, 9}; std::cout << "CLING_CASE_007=" << values.count(4) << std::endl;'

run_case 008 unordered_set_lookup CLING_CASE_008=4 \
  '#include <iostream>' \
  '#include <unordered_set>' \
  'std::unordered_set<int> values{2, 3, 5, 3}; std::cout << "CLING_CASE_008=" << values.size() + values.count(5) << std::endl;'

run_case 009 map_index_and_at CLING_CASE_009=12 \
  '#include <iostream>' \
  '#include <map>' \
  '#include <string>' \
  'std::map<std::string, int> values; values["alpha"] = 7; values["beta"] = 5; std::cout << "CLING_CASE_009=" << values.at("alpha") + values.at("beta") << std::endl;'

run_case 010 multimap_equal_range CLING_CASE_010=2 \
  '#include <iostream>' \
  '#include <iterator>' \
  '#include <map>' \
  'std::multimap<int, int> values{{2, 5}, {1, 9}, {2, 7}}; auto range = values.equal_range(2); std::cout << "CLING_CASE_010=" << std::distance(range.first, range.second) << std::endl;'

run_case 011 unordered_map_at CLING_CASE_011=11 \
  '#include <iostream>' \
  '#include <string>' \
  '#include <unordered_map>' \
  'std::unordered_map<std::string, int> values{{"cling", 11}}; std::cout << "CLING_CASE_011=" << values.at("cling") << std::endl;'

run_case 012 stack_top_size CLING_CASE_012=92 \
  '#include <iostream>' \
  '#include <stack>' \
  'std::stack<int> values; values.push(3); values.push(9); std::cout << "CLING_CASE_012=" << values.top() * 10 + static_cast<int>(values.size()) << std::endl;'

run_case 013 queue_front_back CLING_CASE_013=10 \
  '#include <iostream>' \
  '#include <queue>' \
  'std::queue<int> values; values.push(4); values.push(6); std::cout << "CLING_CASE_013=" << values.front() + values.back() << std::endl;'

run_case 014 priority_queue_top CLING_CASE_014=8 \
  '#include <iostream>' \
  '#include <queue>' \
  '#include <vector>' \
  'std::priority_queue<int> values; values.push(3); values.push(8); values.push(5); std::cout << "CLING_CASE_014=" << values.top() << std::endl;'

run_case 015 string_substr CLING_CASE_015=har \
  '#include <iostream>' \
  '#include <string>' \
  'std::string value = "harmony"; std::cout << "CLING_CASE_015=" << value.substr(0, 3) << std::endl;'

run_case 016 string_find CLING_CASE_016=5 \
  '#include <iostream>' \
  '#include <string>' \
  'std::string value = "interpreter"; std::cout << "CLING_CASE_016=" << value.find("pret") << std::endl;'

run_case 017 string_replace CLING_CASE_017=abc123 \
  '#include <iostream>' \
  '#include <string>' \
  'std::string value = "abcXYZ"; value.replace(3, 3, "123"); std::cout << "CLING_CASE_017=" << value << std::endl;'

run_case 018 string_view_prefix CLING_CASE_018=view \
  '#include <iostream>' \
  '#include <string_view>' \
  'std::string_view value = "cling-view"; value.remove_prefix(6); std::cout << "CLING_CASE_018=" << value << std::endl;'

run_case 019 tuple_apply CLING_CASE_019=10 \
  '#include <iostream>' \
  '#include <tuple>' \
  'auto values = std::make_tuple(2, 3, 5); std::cout << "CLING_CASE_019=" << std::apply([](int a, int b, int c) { return a + b + c; }, values) << std::endl;'

run_case 020 pair_swap CLING_CASE_020=73 \
  '#include <iostream>' \
  '#include <utility>' \
  'std::pair<int, int> left{1, 9}; std::pair<int, int> right{7, 3}; left.swap(right); std::cout << "CLING_CASE_020=" << left.first * 10 + left.second << std::endl;'

run_case 021 optional_value_or CLING_CASE_021=17 \
  '#include <iostream>' \
  '#include <optional>' \
  'std::optional<int> value; std::cout << "CLING_CASE_021=" << value.value_or(17) << std::endl;'

run_case 022 variant_get CLING_CASE_022=variant \
  '#include <iostream>' \
  '#include <string>' \
  '#include <variant>' \
  'std::variant<int, std::string> value = std::string("variant"); std::cout << "CLING_CASE_022=" << std::get<std::string>(value) << std::endl;'

run_case 023 any_cast CLING_CASE_023=29 \
  '#include <any>' \
  '#include <iostream>' \
  'std::any value = 29; std::cout << "CLING_CASE_023=" << std::any_cast<int>(value) << std::endl;'

run_case 024 bitset_count CLING_CASE_024=4 \
  '#include <bitset>' \
  '#include <iostream>' \
  'std::bitset<6> value("101101"); std::cout << "CLING_CASE_024=" << value.count() << std::endl;'

run_case 025 complex_multiply CLING_CASE_025=5,5 \
  '#include <complex>' \
  '#include <iostream>' \
  'std::complex<int> value = std::complex<int>(1, 2) * std::complex<int>(3, -1); std::cout << "CLING_CASE_025=" << value.real() << "," << value.imag() << std::endl;'

run_case 026 ratio_add CLING_CASE_026=1/2 \
  '#include <iostream>' \
  '#include <ratio>' \
  'using value = std::ratio_add<std::ratio<1, 3>, std::ratio<1, 6>>; std::cout << "CLING_CASE_026=" << value::num << "/" << value::den << std::endl;'

run_case 027 chrono_duration_cast CLING_CASE_027=2000 \
  '#include <chrono>' \
  '#include <iostream>' \
  'auto value = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::seconds(2)); std::cout << "CLING_CASE_027=" << value.count() << std::endl;'

run_case 028 numeric_limits CLING_CASE_028=255 \
  '#include <iostream>' \
  '#include <limits>' \
  'std::cout << "CLING_CASE_028=" << static_cast<unsigned int>(std::numeric_limits<unsigned char>::max()) << std::endl;'

run_case 029 type_traits_remove_cv CLING_CASE_029=1 \
  '#include <iostream>' \
  '#include <type_traits>' \
  'std::cout << "CLING_CASE_029=" << std::is_same_v<std::remove_cv_t<const int>, int> << std::endl;'

run_case 030 unique_ptr_value CLING_CASE_030=31 \
  '#include <iostream>' \
  '#include <memory>' \
  'auto value = std::make_unique<int>(31); std::cout << "CLING_CASE_030=" << *value << std::endl;'

run_case 031 shared_ptr_count CLING_CASE_031=2 \
  '#include <iostream>' \
  '#include <memory>' \
  'auto first = std::make_shared<int>(6); auto second = first; std::cout << "CLING_CASE_031=" << first.use_count() << std::endl;'

run_case 032 weak_ptr_expiry CLING_CASE_032=1 \
  '#include <iostream>' \
  '#include <memory>' \
  'auto owner = std::make_shared<int>(8); std::weak_ptr<int> observer = owner; owner.reset(); std::cout << "CLING_CASE_032=" << observer.expired() << std::endl;'

run_case 033 function_lambda CLING_CASE_033=21 \
  '#include <functional>' \
  '#include <iostream>' \
  'std::function<int(int)> triple = [](int value) { return value * 3; }; std::cout << "CLING_CASE_033=" << triple(7) << std::endl;'

run_case 034 bind_placeholder CLING_CASE_034=13 \
  '#include <functional>' \
  '#include <iostream>' \
  'auto add_five = std::bind(std::plus<int>(), 5, std::placeholders::_1); std::cout << "CLING_CASE_034=" << add_five(8) << std::endl;'

run_case 035 reference_wrapper CLING_CASE_035=14 \
  '#include <functional>' \
  '#include <iostream>' \
  'int value = 9; std::reference_wrapper<int> reference(value); reference.get() += 5; std::cout << "CLING_CASE_035=" << value << std::endl;'

run_case 036 algorithm_sort CLING_CASE_036=159 \
  '#include <algorithm>' \
  '#include <iostream>' \
  '#include <vector>' \
  'std::vector<int> values{9, 1, 5}; std::sort(values.begin(), values.end()); std::cout << "CLING_CASE_036=" << values[0] << values[1] << values[2] << std::endl;'

run_case 037 algorithm_merge CLING_CASE_037=1234 \
  '#include <algorithm>' \
  '#include <iostream>' \
  'int a[]={1,4},b[]={2,3},c[4]; std::merge(a,a+2,b,b+2,c); std::cout << "CLING_CASE_037=" << c[0] << c[1] << c[2] << c[3] << std::endl;'

run_case 038 algorithm_reverse CLING_CASE_038=stressed \
  '#include <algorithm>' \
  '#include <iostream>' \
  '#include <string>' \
  'std::string value = "desserts"; std::reverse(value.begin(), value.end()); std::cout << "CLING_CASE_038=" << value << std::endl;'

run_case 039 algorithm_rotate CLING_CASE_039=2341 \
  '#include <algorithm>' \
  '#include <iostream>' \
  '#include <vector>' \
  'std::vector<int> values{1, 2, 3, 4}; std::rotate(values.begin(), values.begin() + 1, values.end()); std::cout << "CLING_CASE_039=" << values[0] << values[1] << values[2] << values[3] << std::endl;'

run_case 040 algorithm_partition CLING_CASE_040=2 \
  '#include <algorithm>' \
  '#include <iostream>' \
  '#include <iterator>' \
  '#include <vector>' \
  'std::vector<int> values{1, 2, 3, 4, 5}; auto boundary = std::partition(values.begin(), values.end(), [](int value) { return value % 2 == 0; }); std::cout << "CLING_CASE_040=" << std::distance(values.begin(), boundary) << std::endl;'

run_case 041 lower_bound_lookup CLING_CASE_041=7 \
  '#include <algorithm>' \
  '#include <iostream>' \
  '#include <vector>' \
  'std::vector<int> values{1, 4, 7, 9}; std::cout << "CLING_CASE_041=" << *std::lower_bound(values.begin(), values.end(), 6) << std::endl;'

run_case 042 binary_search CLING_CASE_042=1 \
  '#include <algorithm>' \
  '#include <iostream>' \
  '#include <vector>' \
  'std::vector<int> values{2, 4, 6, 8}; std::cout << "CLING_CASE_042=" << std::binary_search(values.begin(), values.end(), 6) << std::endl;'

run_case 043 count_if CLING_CASE_043=3 \
  '#include <algorithm>' \
  '#include <iostream>' \
  '#include <vector>' \
  'std::vector<int> values{1, 2, 3, 4, 5, 6}; std::cout << "CLING_CASE_043=" << std::count_if(values.begin(), values.end(), [](int value) { return value % 2 != 0; }) << std::endl;'

run_case 044 next_permutation CLING_CASE_044=132 \
  '#include <algorithm>' \
  '#include <iostream>' \
  'int values[]={1,2,3}; std::next_permutation(values,values+3); std::cout << "CLING_CASE_044=" << values[0] << values[1] << values[2] << std::endl;'

run_case 045 unique_erase CLING_CASE_045=3 \
  '#include <algorithm>' \
  '#include <iostream>' \
  '#include <vector>' \
  'std::vector<int> values{1, 1, 2, 2, 2, 3}; values.erase(std::unique(values.begin(), values.end()), values.end()); std::cout << "CLING_CASE_045=" << values.size() << std::endl;'

run_case 046 minmax_element CLING_CASE_046=-4,9 \
  '#include <algorithm>' \
  '#include <iostream>' \
  '#include <vector>' \
  'std::vector<int> values{-4, 9, 2}; auto bounds = std::minmax_element(values.begin(), values.end()); std::cout << "CLING_CASE_046=" << *bounds.first << "," << *bounds.second << std::endl;'

run_case 047 all_of CLING_CASE_047=1 \
  '#include <algorithm>' \
  '#include <iostream>' \
  '#include <vector>' \
  'std::vector<int> values{2, 6, 10}; std::cout << "CLING_CASE_047=" << std::all_of(values.begin(), values.end(), [](int value) { return value > 0 && value % 2 == 0; }) << std::endl;'

run_case 048 accumulate_product CLING_CASE_048=24 \
  '#include <functional>' \
  '#include <iostream>' \
  '#include <numeric>' \
  '#include <vector>' \
  'std::vector<int> values{2, 3, 4}; std::cout << "CLING_CASE_048=" << std::accumulate(values.begin(), values.end(), 1, std::multiplies<int>()) << std::endl;'

run_case 049 inner_product CLING_CASE_049=32 \
  '#include <iostream>' \
  '#include <numeric>' \
  '#include <vector>' \
  'std::vector<int> left{1, 2, 3}; std::vector<int> right{4, 5, 6}; std::cout << "CLING_CASE_049=" << std::inner_product(left.begin(), left.end(), right.begin(), 0) << std::endl;'

run_case 050 partial_sum CLING_CASE_050=10 \
  '#include <iostream>' \
  '#include <numeric>' \
  '#include <vector>' \
  'std::vector<int> values{1, 2, 3, 4}; std::vector<int> sums(4); std::partial_sum(values.begin(), values.end(), sums.begin()); std::cout << "CLING_CASE_050=" << sums.back() << std::endl;'

run_case 051 adjacent_difference CLING_CASE_051=7 \
  '#include <iostream>' \
  '#include <numeric>' \
  '#include <vector>' \
  'std::vector<int> values{3, 8, 15}; std::vector<int> differences(3); std::adjacent_difference(values.begin(), values.end(), differences.begin()); std::cout << "CLING_CASE_051=" << differences.back() << std::endl;'

run_case 052 iota_sequence CLING_CASE_052=30 \
  '#include <iostream>' \
  '#include <numeric>' \
  '#include <vector>' \
  'std::vector<int> values(4); std::iota(values.begin(), values.end(), 6); std::cout << "CLING_CASE_052=" << std::accumulate(values.begin(), values.end(), 0) << std::endl;'

passed=$((total - failures))
printf 'CLING_MATRIX_RESULT=%s/%s\n' "$passed" "$total"

if [[ $total -ne 52 ]]; then
  echo "[fail] harness expected 52 cases, discovered $total" >&2
  exit 1
fi

if [[ $failures -ne 0 ]]; then
  exit 1
fi
