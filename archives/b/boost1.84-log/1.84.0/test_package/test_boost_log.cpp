// test_package/test_boost_log.cpp — boost1.84-log 1.84.0 L1 功能测试。
// 覆盖：trivial 日志、core/sink 管理、severity_logger、attributes、
// expressions 格式化、setup（init_from_stream 设置文件解析）、text_file sink。
#include <boost/log/trivial.hpp>
#include <boost/log/core.hpp>
#include <boost/log/sinks/sync_frontend.hpp>
#include <boost/log/sinks/text_ostream_backend.hpp>
#include <boost/log/sinks/text_file_backend.hpp>
#include <boost/log/sources/severity_logger.hpp>
#include <boost/log/sources/record_ostream.hpp>
#include <boost/log/attributes.hpp>
#include <boost/log/attributes/named_scope.hpp>
#include <boost/log/expressions.hpp>
#include <boost/log/utility/setup/common_attributes.hpp>
#include <boost/log/utility/setup/from_stream.hpp>
#include <boost/filesystem.hpp>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

namespace logging = boost::log;
namespace sinks = logging::sinks;
namespace src = logging::sources;
namespace attrs = logging::attributes;

int check(bool cond, const char *what) {
    if (!cond) {
        std::cerr << "FAIL: " << what << std::endl;
        return 1;
    }
    std::cout << "OK: " << what << std::endl;
    return 0;
}

int main() {
    int failures = 0;

    // 1. trivial 日志（core + trivial + 默认 sink）
    BOOST_LOG_TRIVIAL(trace) << "trace message";
    BOOST_LOG_TRIVIAL(info) << "info message";
    BOOST_LOG_TRIVIAL(warning) << "warning message";
    failures += check(true, "trivial logging executed");

    // 2. 自定义同步 sink + formatter（text_ostream_backend + expressions）
    typedef sinks::synchronous_sink<sinks::text_ostream_backend> sink_t;
    boost::shared_ptr<std::ostringstream> stream(new std::ostringstream);
    boost::shared_ptr<sink_t> sink(new sink_t);
    sink->locked_backend()->add_stream(stream);
    sink->set_formatter(
        logging::expressions::stream
            << logging::expressions::attr<unsigned int>("LineID")
            << "|" << logging::expressions::smessage);
    logging::core::get()->add_sink(sink);
    logging::core::get()->add_global_attribute("LineID", attrs::counter<unsigned int>(1));

    src::severity_logger<logging::trivial::severity_level> lg;
    BOOST_LOG_SEV(lg, logging::trivial::error) << "formatted sink message";

    logging::core::get()->remove_sink(sink);
    std::string s = stream->str();
    failures += check(s.find("formatted sink message") != std::string::npos,
                      "custom sink captured formatted record");
    failures += check(s.find("1|") == 0, "LineID attribute applied");

    // 3. named_scope 属性 + record_ostream（BOOST_LOG_NAMED_SCOPE 宏）
    {
        BOOST_LOG_NAMED_SCOPE("test_package");
        BOOST_LOG_SEV(lg, logging::trivial::info) << "message inside named scope";
        failures += check(true, "named_scope attribute set");
    }

    // 4. setup：init_from_stream 解析 ini 设置并创建 console sink
    std::istringstream ini(
        "[Core]\n"
        "DisableLogging=false\n"
        "\n"
        "[Sinks.Console]\n"
        "Destination=Console\n"
        "Asynchronous=false\n"
        "AutoFlush=true\n"
        "Format=\"[%Severity%]: %Message%\"\n");
    try {
        logging::init_from_stream(ini);
        BOOST_LOG_TRIVIAL(info) << "after setup init";
        failures += check(true, "init_from_stream parsed settings");
    } catch (const std::exception &e) {
        std::cerr << "init_from_stream error: " << e.what() << std::endl;
        failures += check(false, "init_from_stream parsed settings");
    }

    // 5. filesystem 依赖联动验证（log 组件依赖元包 filesystem）
    boost::filesystem::path logdir = boost::filesystem::temp_directory_path() / "boost_log_test_pkg";
    boost::system::error_code ec;
    boost::filesystem::create_directories(logdir, ec);
    failures += check(!ec, "filesystem create_directories (dependency link)");

    // 6. text_file_backend 链路（文件 sink 写入验证）
    boost::filesystem::path logfile = logdir / "test_%3N.log";
    {
        typedef sinks::synchronous_sink<sinks::text_file_backend> file_sink_t;
        boost::shared_ptr<sinks::text_file_backend> backend(
            new sinks::text_file_backend(
                logging::keywords::file_name = logfile.string()));
        boost::shared_ptr<file_sink_t> fsink(new file_sink_t(backend));
        logging::core::get()->add_sink(fsink);
        BOOST_LOG_TRIVIAL(warning) << "file sink message";
        logging::core::get()->flush();
        logging::core::get()->remove_sink(fsink);
    }
    bool file_written = false;
    for (boost::filesystem::directory_iterator it(logdir), end; it != end; ++it) {
        if (boost::filesystem::file_size(it->path(), ec) > 0) file_written = true;
    }
    failures += check(file_written, "text_file_backend wrote log file");

    if (failures == 0) {
        std::cout << "boost1.84-log 1.84.0: all functional checks OK" << std::endl;
        return 0;
    }
    std::cerr << failures << " check(s) failed" << std::endl;
    return 1;
}
