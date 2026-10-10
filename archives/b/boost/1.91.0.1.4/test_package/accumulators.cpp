#include <boost/accumulators/accumulators.hpp>
#include <boost/accumulators/statistics/count.hpp>
#include <boost/accumulators/statistics/mean.hpp>
#include <boost/accumulators/statistics/stats.hpp>

int main() {
    namespace ba = boost::accumulators;
    ba::accumulator_set<double, ba::stats<ba::tag::mean, ba::tag::count>> values;
    values(1.0);
    values(3.0);
    return ba::count(values) == 2 && ba::mean(values) == 2.0 ? 0 : 1;
}
