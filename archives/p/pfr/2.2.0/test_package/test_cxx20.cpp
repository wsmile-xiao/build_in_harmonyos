#include <boost/pfr/core_name.hpp>

struct named_record {
    int count;
    double ratio;
};

static_assert(boost::pfr::get_name<0, named_record>() == "count");
static_assert(boost::pfr::get_name<1, named_record>() == "ratio");

int main() {
    return boost::pfr::get_name<0, named_record>() == "count" &&
                   boost::pfr::get_name<1, named_record>() == "ratio"
               ? 0
               : 1;
}
