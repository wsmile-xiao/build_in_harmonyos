// logr 消费者验证用例（HarmonyOS PC / OHOS 专用消费者程序）
//
// 模拟业务上层组件使用方式：仅通过 logr 已安装/导出的公开头文件
// （<logr/logr.hpp>、<logr/ostream_backend.hpp>、<logr/version.hpp>）、
// 公开 API（logr::ostream_logger_t、logger.info/error、format_to）与
// 正常链接目标（logr::logr_base + fmt::fmt）使用该三方库，验证第三方
// 使用者能否编译、链接、调用并正常运行。
//
// 本用例必须是真实逻辑：向 std::ostringstream 输出日志并断言内容与
// 版本、级别路由均正确；不是"只打印字符串/只检查文件存在"的空壳。

#include <sstream>
#include <string>

#include <logr/logr.hpp>
#include <logr/ostream_backend.hpp>
#include <logr/version.hpp>

int main()
{
    std::ostringstream sink;

    // 级别过滤验证：level=info 时 trace/debug 被过滤，info/error 输出
    //（ostream backend 为 demo logger，trace 级别下 debug 消息同样会写出
    // "TRACE:" 前缀，因此必须以 info 级别构造才能验证过滤行为）。
    auto logger = logr::ostream_logger_t<>{ sink, logr::log_message_level::info };

    // 1) 普通格式化输出（fmt::format_to 写入 logr 内部缓冲区）
    logger.info( []( auto & out ) {
        format_to( out, "hello from logr v{}.{}.{}",
                   LOGR_VERSION_MAJOR, LOGR_VERSION_MINOR, LOGR_VERSION_PATCH );
    } );

    // 2) 动态级别过滤：debug 级别低于 info，不输出
    logger.debug( []( auto & out ) {
        format_to( out, "this debug message must not appear" );
    } );

    // 3) 显式级别输出
    logger.error( []( auto & out ) {
        format_to( out, "an error occurred" );
    } );

    const std::string text = sink.str();

    const bool version_ok = text.find( "hello from logr v0.8.0" ) != std::string::npos;
    const bool debug_hidden = text.find( "must not appear" ) == std::string::npos;
    const bool error_ok = text.find( "an error occurred" ) != std::string::npos;

    if ( !version_ok || !debug_hidden || !error_ok )
    {
        return 1;
    }

    return 0;
}