// Zero-dependency shim of <boost/mpl/list.hpp>: a pure compile-time type
// sequence is all the ordered-map tests need from Boost.MPL (header-only
// upstream, but pulled here to keep the harness dependency-free).
#ifndef SHIM_BOOST_MPL_LIST_HPP
#define SHIM_BOOST_MPL_LIST_HPP

#include <tuple>

namespace boost {
namespace mpl {
template <typename... Ts>
using list = std::tuple<Ts...>;
}  // namespace mpl
}  // namespace boost

#endif  // SHIM_BOOST_MPL_LIST_HPP
