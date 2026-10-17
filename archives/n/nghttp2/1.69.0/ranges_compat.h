// ranges_compat.h — C++20 std::ranges compatibility for OHOS libc++ (LLVM 15)
// OHOS libc++ supports std::ranges::begin/end/size/data and concepts
// (forward_range, sized_range, etc.) but NOT range-based algorithms or views.
// This header provides the missing algorithms and views by wrapping std:: counterparts.
// Also provides std::source_location (missing in OHOS libc++).
#pragma once

#include <algorithm>
#include <iterator>
#include <ranges>
#include <utility>
#include <span>
#include <functional>
#include <vector>

// --- std::source_location compatibility ---
namespace std {

struct source_location {
private:
  const char* file_ = "";
  const char* func_ = "";
  int line_ = 0;
  int col_ = 0;

public:
  constexpr source_location() noexcept = default;

  static constexpr source_location current(
      const char* file = __builtin_FILE(),
      const char* func = __builtin_FUNCTION(),
      int line = __builtin_LINE(),
      int col = 0) noexcept {
    source_location loc;
    loc.file_ = file;
    loc.func_ = func;
    loc.line_ = line;
    loc.col_ = col;
    return loc;
  }

  constexpr const char* file_name() const noexcept { return file_; }
  constexpr const char* function_name() const noexcept { return func_; }
  constexpr int line() const noexcept { return line_; }
  constexpr int column() const noexcept { return col_; }
};

} // namespace std

namespace std::ranges {

// Helper: return type for copy/copy_n/move (provides .out member)
template <typename I, typename O>
struct out_result {
  I in;
  O out;
};

// Helper: return type for copy_n with pointer
template <typename I, typename O>
struct in_out_result {
  I in;
  O out;
};

// Simple subrange view for take/drop
template <typename I>
struct subrange_view {
  I first_;
  I last_;
  constexpr I begin() const { return first_; }
  constexpr I end() const { return last_; }
};

// --- rbegin / rend ---
template <typename R>
constexpr auto rbegin(R&& r) {
  return std::rbegin(r);
}

template <typename R>
constexpr auto rend(R&& r) {
  return std::rend(r);
}

// --- copy ---
template <typename I, typename S, typename O>
constexpr auto copy(I first, S last, O result) {
  auto out = std::copy(first, last, result);
  return out_result<I, O>{static_cast<I>(last), out};
}

template <typename R, typename O>
constexpr auto copy(R&& r, O result) {
  auto first = std::ranges::begin(r);
  auto last = std::ranges::end(r);
  auto out = std::copy(first, last, result);
  return out_result<decltype(first), O>{last, out};
}

// --- copy_n ---
template <typename I, typename N, typename O>
constexpr auto copy_n(I first, N n, O result) {
  auto out = std::copy_n(first, n, result);
  return out_result<I, O>{first + n, out};
}

// --- fill ---
template <typename R, typename T>
constexpr void fill(R&& r, const T& val) {
  std::fill(std::ranges::begin(r), std::ranges::end(r), val);
}

template <typename I, typename S, typename T>
constexpr void fill(I first, S last, const T& val) {
  std::fill(first, last, val);
}

// --- fill_n ---
template <typename I, typename N, typename T>
constexpr I fill_n(I first, N n, const T& val) {
  return std::fill_n(first, n, val);
}

// --- find ---
template <typename R, typename T>
constexpr auto find(R&& r, const T& val) {
  return std::find(std::ranges::begin(r), std::ranges::end(r), val);
}

template <typename I, typename S, typename T>
constexpr auto find(I first, S last, const T& val) {
  return std::find(first, last, val);
}

// --- find_if ---
template <typename R, typename Pred>
constexpr auto find_if(R&& r, Pred pred) {
  return std::find_if(std::ranges::begin(r), std::ranges::end(r), pred);
}

template <typename I, typename S, typename Pred>
constexpr auto find_if(I first, S last, Pred pred) {
  return std::find_if(first, last, pred);
}

// --- find_if_not ---
template <typename R, typename Pred>
constexpr auto find_if_not(R&& r, Pred pred) {
  return std::find_if_not(std::ranges::begin(r), std::ranges::end(r), pred);
}

template <typename I, typename S, typename Pred>
constexpr auto find_if_not(I first, S last, Pred pred) {
  return std::find_if_not(first, last, pred);
}

// --- find_first_of ---
template <typename I1, typename S1, typename I2, typename S2, typename Pred>
constexpr auto find_first_of(I1 first1, S1 last1, I2 first2, S2 last2, Pred pred) {
  return std::find_first_of(first1, last1, first2, last2, pred);
}

template <typename I1, typename S1, typename I2, typename S2>
constexpr auto find_first_of(I1 first1, S1 last1, I2 first2, S2 last2) {
  return std::find_first_of(first1, last1, first2, last2);
}

template <typename R1, typename R2, typename Pred>
constexpr auto find_first_of(R1&& r1, R2&& r2, Pred pred) {
  return std::find_first_of(std::ranges::begin(r1), std::ranges::end(r1),
                            std::ranges::begin(r2), std::ranges::end(r2), pred);
}

// --- lower_bound ---
template <typename I, typename S, typename T, typename Proj, typename Comp>
constexpr auto lower_bound(I first, S last, const T& val, Comp comp, Proj proj) {
  return std::lower_bound(first, last, val,
    [&](const auto& a, const auto& b) { return comp(std::invoke(proj, a), b); });
}

template <typename I, typename S, typename T>
constexpr auto lower_bound(I first, S last, const T& val) {
  return std::lower_bound(first, last, val);
}

// Range overloads with default Comp type for {} argument support
template <typename R, typename T, typename Proj, typename Comp = std::ranges::less>
constexpr auto lower_bound(R&& r, const T& val, Comp comp, Proj proj) {
  return std::lower_bound(std::ranges::begin(r), std::ranges::end(r), val,
    [&](const auto& a, const auto& b) { return comp(std::invoke(proj, a), b); });
}

template <typename R, typename T>
constexpr auto lower_bound(R&& r, const T& val) {
  return std::lower_bound(std::ranges::begin(r), std::ranges::end(r), val);
}

// --- transform ---
template <typename I, typename S, typename O, typename F>
constexpr auto transform(I first, S last, O result, F f) {
  auto out = std::transform(first, last, result, f);
  return out_result<I, O>{static_cast<I>(last), out};
}

template <typename R, typename O, typename F>
constexpr auto transform(R&& r, O result, F f) {
  auto first = std::ranges::begin(r);
  auto last = std::ranges::end(r);
  auto out = std::transform(first, last, result, f);
  return out_result<decltype(first), O>{last, out};
}

// --- sort ---
template <typename R>
constexpr void sort(R&& r) {
  std::sort(std::ranges::begin(r), std::ranges::end(r));
}

template <typename R, typename Comp>
constexpr void sort(R&& r, Comp comp) {
  std::sort(std::ranges::begin(r), std::ranges::end(r), comp);
}

// --- distance ---
template <typename I, typename S>
constexpr auto distance(I first, S last) {
  return std::distance(first, last);
}

template <typename R>
constexpr auto distance(R&& r) {
  return std::distance(std::ranges::begin(r), std::ranges::end(r));
}

// --- next ---
template <typename I>
constexpr I next(I it) {
  return std::next(it);
}

template <typename I, typename N>
constexpr I next(I it, N n) {
  return std::next(it, n);
}

// --- advance ---
template <typename I, typename N>
constexpr void advance(I& it, N n) {
  std::advance(it, n);
}

// --- all_of ---
template <typename I, typename S, typename Pred>
constexpr bool all_of(I first, S last, Pred pred) {
  return std::all_of(first, last, pred);
}

template <typename R, typename Pred>
constexpr bool all_of(R&& r, Pred pred) {
  return std::all_of(std::ranges::begin(r), std::ranges::end(r), pred);
}

// --- any_of ---
template <typename I, typename S, typename Pred>
constexpr bool any_of(I first, S last, Pred pred) {
  return std::any_of(first, last, pred);
}

template <typename R, typename Pred>
constexpr bool any_of(R&& r, Pred pred) {
  return std::any_of(std::ranges::begin(r), std::ranges::end(r), pred);
}

// --- equal ---
template <typename I1, typename S1, typename I2, typename S2>
constexpr bool equal(I1 first1, S1 last1, I2 first2, S2 last2) {
  return std::equal(first1, last1, first2, last2);
}

template <typename I1, typename S1, typename I2, typename S2, typename Pred>
constexpr bool equal(I1 first1, S1 last1, I2 first2, S2 last2, Pred pred) {
  return std::equal(first1, last1, first2, last2, pred);
}

template <typename R1, typename R2>
constexpr bool equal(R1&& r1, R2&& r2) {
  return std::equal(std::ranges::begin(r1), std::ranges::end(r1),
                    std::ranges::begin(r2), std::ranges::end(r2));
}

template <typename R1, typename R2, typename Pred>
constexpr bool equal(R1&& r1, R2&& r2, Pred pred) {
  return std::equal(std::ranges::begin(r1), std::ranges::end(r1),
                    std::ranges::begin(r2), std::ranges::end(r2), pred);
}

// --- count ---
template <typename I, typename S, typename T>
constexpr auto count(I first, S last, const T& val) {
  return std::count(first, last, val);
}

template <typename R, typename T>
constexpr auto count(R&& r, const T& val) {
  return std::count(std::ranges::begin(r), std::ranges::end(r), val);
}

// --- count_if ---
template <typename R, typename Pred, typename Proj = std::identity>
constexpr auto count_if(R&& r, Pred pred, Proj proj = {}) {
  return std::count_if(std::ranges::begin(r), std::ranges::end(r),
    [&](const auto& v) { return pred(std::invoke(proj, v)); });
}

// --- max_element ---
template <typename I, typename S>
constexpr auto max_element(I first, S last) {
  return std::max_element(first, last);
}

template <typename R>
constexpr auto max_element(R&& r) {
  return std::max_element(std::ranges::begin(r), std::ranges::end(r));
}

// --- min ---
template <typename T>
constexpr T min(std::initializer_list<T> ilist) {
  return std::min(ilist);
}

template <typename T, typename Compare>
constexpr T min(std::initializer_list<T> ilist, Compare comp) {
  return std::min(ilist, comp);
}

template <typename R>
constexpr auto min(R&& r) {
  return *std::min_element(std::ranges::begin(r), std::ranges::end(r));
}

template <typename R, typename Compare>
constexpr auto min(R&& r, Compare comp) {
  return *std::min_element(std::ranges::begin(r), std::ranges::end(r), comp);
}

// Helper: simple subrange for algorithm return types
template <typename I>
struct simple_subrange {
  I first_;
  I last_;
  constexpr I begin() const { return first_; }
  constexpr I end() const { return last_; }
};

// --- remove_if ---
template <typename R, typename Pred, typename Proj = std::identity>
constexpr auto remove_if(R&& r, Pred pred, Proj proj = {}) {
  auto it = std::remove_if(std::ranges::begin(r), std::ranges::end(r),
    [&](const auto& v) { return pred(std::invoke(proj, v)); });
  auto end = std::ranges::end(r);
  return simple_subrange<decltype(it)>{it, end};
}

// --- generate ---
template <typename I, typename S, typename G>
constexpr void generate(I first, S last, G g) {
  std::generate(first, last, g);
}

template <typename R, typename G>
constexpr void generate(R&& r, G g) {
  std::generate(std::ranges::begin(r), std::ranges::end(r), g);
}

// --- reverse ---
template <typename R>
constexpr void reverse(R&& r) {
  std::reverse(std::ranges::begin(r), std::ranges::end(r));
}

template <typename I, typename S>
constexpr void reverse(I first, S last) {
  std::reverse(first, last);
}

// --- reverse_copy ---
template <typename I, typename S, typename O>
constexpr auto reverse_copy(I first, S last, O result) {
  auto out = std::reverse_copy(first, last, result);
  return out_result<I, O>{static_cast<I>(last), out};
}

template <typename R, typename O>
constexpr auto reverse_copy(R&& r, O result) {
  auto first = std::ranges::begin(r);
  auto last = std::ranges::end(r);
  auto out = std::reverse_copy(first, last, result);
  return out_result<decltype(first), O>{last, out};
}

// --- rotate ---
template <typename I, typename S>
constexpr auto rotate(I first, I middle, S last) {
  return std::rotate(first, middle, last);
}

template <typename R, typename I>
constexpr auto rotate(R&& r, I middle) {
  return std::rotate(std::ranges::begin(r), middle, std::ranges::end(r));
}

} // namespace std::ranges

// --- std::views (minimal: take and drop) ---
namespace std::views {

namespace detail {

template <typename R>
struct take_view {
  using I = decltype(std::ranges::begin(std::declval<R&>()));
  I first_;
  I last_;
  constexpr I begin() const { return first_; }
  constexpr I end() const { return last_; }
};

template <typename R>
struct drop_view {
  using I = decltype(std::ranges::begin(std::declval<R&>()));
  I first_;
  I last_;
  constexpr I begin() const { return first_; }
  constexpr I end() const { return last_; }
};

} // namespace detail

template <typename R, typename N>
constexpr auto take(R&& r, N n) {
  auto first = std::ranges::begin(r);
  auto last = std::ranges::end(r);
  auto count = static_cast<std::ptrdiff_t>(n);
  // Advance first by n, but not past last
  auto it = first;
  for (std::ptrdiff_t i = 0; i < count && it != last; ++i, ++it) {}
  using I = decltype(first);
  detail::take_view<R> v{first, it};
  return v;
}

template <typename R, typename N>
constexpr auto drop(R&& r, N n) {
  auto first = std::ranges::begin(r);
  auto last = std::ranges::end(r);
  auto count = static_cast<std::ptrdiff_t>(n);
  // Advance first by n, but not past last
  for (std::ptrdiff_t i = 0; i < count && first != last; ++i, ++first) {}
  using I = decltype(first);
  detail::drop_view<R> v{first, last};
  return v;
}

} // namespace std::views

// --- std::views::transform (eager evaluation for compatibility) ---
namespace std::views {

namespace detail {

template <typename R, typename F>
struct transform_view {
  using Val = decltype(std::declval<F>()(*std::ranges::begin(std::declval<R&>())));
  std::vector<Val> data_;

  transform_view(R&& r, F f) {
    auto first = std::ranges::begin(r);
    auto last = std::ranges::end(r);
    for (; first != last; ++first) {
      data_.push_back(f(*first));
    }
  }

  auto begin() { return data_.begin(); }
  auto end() { return data_.end(); }
  auto size() const { return data_.size(); }
  auto begin() const { return data_.begin(); }
  auto end() const { return data_.end(); }
};

} // namespace detail

template <typename R, typename F>
auto transform(R&& r, F f) {
  return detail::transform_view<R, F>(std::forward<R>(r), std::move(f));
}

} // namespace std::views
