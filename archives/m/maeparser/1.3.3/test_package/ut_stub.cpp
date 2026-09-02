// Boost.Test implementation stub — zero-patch replacement for the missing
// libboost_unit_test_framework. This is the officially supported "manual
// static compile" mode: defining BOOST_TEST_SOURCE and including every
// boost/test/impl/*.ipp compiles the exact same implementation sources that
// the boost project builds into libboost_unit_test_framework.
// Available from the boost/1.84.0 package: boost/test/impl/*.ipp
#define BOOST_TEST_SOURCE
#include <boost/test/impl/compiler_log_formatter.ipp>
#include <boost/test/impl/junit_log_formatter.ipp>
#include <boost/test/impl/debug.ipp>
#include <boost/test/impl/decorator.ipp>
#include <boost/test/impl/framework.ipp>
#include <boost/test/impl/execution_monitor.ipp>
#include <boost/test/impl/plain_report_formatter.ipp>
#include <boost/test/impl/progress_monitor.ipp>
#include <boost/test/impl/results_collector.ipp>
#include <boost/test/impl/results_reporter.ipp>
#include <boost/test/impl/test_framework_init_observer.ipp>
#include <boost/test/impl/test_tools.ipp>
#include <boost/test/impl/test_tree.ipp>
#include <boost/test/impl/unit_test_log.ipp>
#include <boost/test/impl/unit_test_main.ipp>
#include <boost/test/impl/unit_test_monitor.ipp>
#include <boost/test/impl/unit_test_parameters.ipp>
#include <boost/test/impl/xml_log_formatter.ipp>
#include <boost/test/impl/xml_report_formatter.ipp>
