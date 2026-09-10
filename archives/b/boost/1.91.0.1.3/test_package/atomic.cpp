#include <boost/atomic.hpp>

int main() {
    boost::atomic<int> value{190};
    return value.fetch_add(1) == 190 && value.load() == 191 ? 0 : 1;
}
