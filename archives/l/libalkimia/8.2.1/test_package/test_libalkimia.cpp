/*
 * libalkimia 8.2.1 —— 消费者端到端用例（rule12）
 *
 * 从「消费者」视角只经安装产物（LibAlkimia6Config.cmake -> Alkimia::alkimia）
 * 走三条完整业务回环，不做纯常量断言：
 *
 *   case1 金融金额计算回环：字符串解析 -> 复式记账四则运算 -> 舍入/精度换算
 *          -> toString 回环再解析 -> 比较运算（GMP mpq 多精度金额）
 *   case2 报价源存储回环：AlkOnlineQuotesProfile 持久化 write -> 重开读取
 *          -> 字段一致 -> rename -> remove -> 存储清空
 *   case3 报价引擎消费者契约：AlkOnlineQuote 构造 + 引擎开关回读 + 未知报价源
 *          launch 的失败契约（返回 false、不发起下载）
 *
 * 输出：ok NN ... / FAIL NN ... 行 + RESULT 汇总；退出码 0 当且仅当
 * 全部校验点通过且三条 case 均真实执行（无静默跳过）。
 *
 * 说明：上游 3 个网络型用例（alkonlinequotestest / alkdownloadengine-qt-test /
 * alknewstuffenginetest）在离线口径被 ctest -E 排除。经实测，真实下载路径
 * （AlkOnlineQuote::launch -> AlkDownloadEngine::downloadUrlQt）在 OHOS musl
 * 运行时下 SEGFAULT，qemu 仿真与 DAYU200 真机同样复现（见
 * reports/upstream-test-evidence.md），故本用例不触发真实网络下载。
 */
#include <QCoreApplication>
#include <QDate>
#include <QDebug>
#include <QMap>
#include <QString>

#include <alkimia/alkonlinequote.h>
#include <alkimia/alkonlinequotesource.h>
#include <alkimia/alkonlinequotesprofile.h>
#include <alkimia/alkvalue.h>

#include <cstdio>

static int g_checks = 0;
static int g_failures = 0;

static void check(bool ok, const char *desc)
{
    ++g_checks;
    if (ok) {
        std::printf("ok %02d %s\n", g_checks, desc);
    } else {
        ++g_failures;
        std::printf("FAIL %02d %s\n", g_checks, desc);
    }
    std::fflush(stdout);
}

// ---------------------------------------------------------------------------
// case1 金融金额计算回环（AlkValue）
// ---------------------------------------------------------------------------
static void case1_value_roundtrip()
{
    std::printf("--- case1 金融金额计算回环 (AlkValue) ---\n");

    // 1.1 字符串解析：欧式千分位 + 逗号小数点（上游 stringCtor 同口径）
    AlkValue euro(QString::fromLatin1("x1.234,568 EUR"), QLatin1Char(','));
    check(euro.toString() == QString::fromLatin1("154321/125"),
          "1.1 parse 'x1.234,568 EUR' (comma decimal) -> 154321/125");

    // 1.2 字符串解析：点小数点
    AlkValue v1025(QString::fromLatin1("10.25"), QLatin1Char('.'));
    check(v1025.toString() == QString::fromLatin1("41/4"),
          "1.2 parse '10.25' -> 41/4");

    // 1.3 复式记账求和回环：10.25 + 5.75 - 3.50 = 12.50 = 25/2
    AlkValue v575(QString::fromLatin1("5.75"), QLatin1Char('.'));
    AlkValue v350(QString::fromLatin1("-3.50"), QLatin1Char('.'));
    AlkValue sum = v1025 + v575 + v350;
    check(sum.toString() == QString::fromLatin1("25/2"),
          "1.3 ledger sum 10.25+5.75-3.50 -> 25/2");

    // 1.4/1.5 乘除回环：25/2 * 4 = 50/1; 50/1 / 8 = 25/4
    AlkValue scaled = sum * 4;
    check(scaled.toString() == QString::fromLatin1("50/1"),
          "1.4 multiply 25/2 * 4 -> 50/1");
    AlkValue divided = scaled / AlkValue(8, 1);
    check(divided.toString() == QString::fromLatin1("25/4"),
          "1.5 divide 50/1 / 8 -> 25/4");

    // 1.6/1.7 舍入换算：2.345（469/200）分母 100，向下/向上取整
    AlkValue v2345(QString::fromLatin1("2.345"), QLatin1Char('.'));
    AlkValue floor2 = v2345.convertDenominator(100, AlkValue::RoundFloor);
    AlkValue ceil2 = v2345.convertDenominator(100, AlkValue::RoundCeil);
    check(floor2.toString() == QString::fromLatin1("117/50"),
          "1.6 convertDenominator(100, RoundFloor) 2.345 -> 117/50");
    check(ceil2.toString() == QString::fromLatin1("47/20"),
          "1.7 convertDenominator(100, RoundCeil) 2.345 -> 47/20");

    // 1.8/1.9 toString -> 再解析回环（分数形式 + 小数形式双路）
    AlkValue rtFraction(sum.toString(), QLatin1Char('.'));
    check(rtFraction == sum, "1.8 toString->reparse fraction round-trip equals");
    AlkValue rtDecimal(QString::fromLatin1("12.50"), QLatin1Char('.'));
    check(rtDecimal == sum, "1.9 decimal '12.50' equals ledger sum");

    // 1.10/1.11 double 构造 + 精度/分母换算工具
    AlkValue fromDouble(1.5, 100);
    check(fromDouble.toString() == QString::fromLatin1("3/2"),
          "1.10 double ctor 1.5 -> 3/2");
    check(AlkValue::precisionToDenominator(2).get_ui() == 100
              && AlkValue::denominatorToPrecision(1000).get_ui() == 3,
          "1.11 precision<->denominator helpers (2<->100, 1000->3)");

    // 1.12 比较运算
    check(sum > v575 && v350 < v575 && sum != divided && sum == rtFraction,
          "1.12 comparison operators (>, <, !=, ==)");
}

// ---------------------------------------------------------------------------
// case2 报价源存储回环（AlkOnlineQuotesProfile + AlkOnlineQuoteSource）
// ---------------------------------------------------------------------------
static void case2_quotesource_store_roundtrip()
{
    std::printf("--- case2 报价源存储回环 (AlkOnlineQuoteSource) ---\n");

    AlkOnlineQuotesProfile profile(QString::fromLatin1("libalkimia-e2e"),
                                   AlkOnlineQuotesProfile::Type::Alkimia4);

    // 2.1 内置货币报价源写入持久化存储
    AlkOnlineQuoteSource src =
        AlkOnlineQuoteSource::defaultCurrencyQuoteSource(QString::fromLatin1("e2e-currency"));
    src.setProfile(&profile);
    bool written = src.write();
    check(written, "2.1 defaultCurrencyQuoteSource write() persists");

    // 2.2/2.3 重开实例读取并逐字段校验
    AlkOnlineQuoteSource back(QString::fromLatin1("e2e-currency"), &profile);
    check(back.isValid(), "2.2 reloaded source isValid()");
    check(back.name() == src.name() && back.url() == src.url()
              && back.idRegex() == src.idRegex()
              && back.priceRegex() == src.priceRegex()
              && back.dateRegex() == src.dateRegex()
              && back.dateFormat() == src.dateFormat(),
          "2.3 reloaded fields match written source");
    check(profile.quoteSources().contains(QString::fromLatin1("e2e-currency")),
          "2.4 profile.quoteSources() contains 'e2e-currency'");

    // 2.5/2.6 自定义 CSV 报价源（消费者自建字段）写读回环
    AlkOnlineQuoteSource csv(QString::fromLatin1("e2e-csv"),
                             QString::fromLatin1("http://127.0.0.1/q?a=%1"),
                             QString(),
                             AlkOnlineQuoteSource::Symbol,
                             QString::fromLatin1("#2"),
                             QString::fromLatin1("#1"),
                             QString::fromLatin1("%d-%m-%y"),
                             AlkOnlineQuoteSource::CSV,
                             AlkOnlineQuoteSource::Period,
                             AlkOnlineQuoteSource::Default);
    csv.setProfile(&profile);
    csv.write();
    AlkOnlineQuoteSource csvBack(QString::fromLatin1("e2e-csv"), &profile);
    check(csvBack.isValid() && csvBack.url() == csv.url(),
          "2.5 custom CSV source write/read url round-trip");
    check(csvBack.dataFormat() == AlkOnlineQuoteSource::CSV
              && csvBack.priceRegex() == QString::fromLatin1("#2")
              && csvBack.dateRegex() == QString::fromLatin1("#1")
              && csvBack.dateFormat() == QString::fromLatin1("%d-%m-%y"),
          "2.6 custom CSV source format/regex fields round-trip");

    // 2.7 rename 回环
    src.rename(QString::fromLatin1("e2e-renamed"));
    AlkOnlineQuoteSource renamed(QString::fromLatin1("e2e-renamed"), &profile);
    check(renamed.isValid() && renamed.url() == src.url(),
          "2.7 rename -> reloaded under new name");

    // 2.8 remove 回环：两个源删除后存储清空
    renamed.remove();
    csvBack.remove();
    AlkOnlineQuoteSource gone(QString::fromLatin1("e2e-renamed"), &profile);
    AlkOnlineQuoteSource goneCsv(QString::fromLatin1("e2e-csv"), &profile);
    check(gone.url().isEmpty() && goneCsv.url().isEmpty()
              && !profile.quoteSources().contains(QString::fromLatin1("e2e-csv")),
          "2.8 remove -> store entries gone");
}

// ---------------------------------------------------------------------------
// case3 报价引擎消费者契约（AlkOnlineQuote，不触发真实下载）
// ---------------------------------------------------------------------------
static void case3_quote_engine_consumer_contract()
{
    std::printf("--- case3 报价引擎消费者契约 (AlkOnlineQuote) ---\n");

    AlkOnlineQuotesProfile profile(QString::fromLatin1("libalkimia-e2e-engine"),
                                   AlkOnlineQuotesProfile::Type::Alkimia4);

    // 3.1/3.2 消费者构造报价引擎对象并绑定 profile/超时/单条信号开关回读
    AlkOnlineQuote quote(&profile);
    quote.setTimeout(5000);
    quote.setUseSingleQuoteSignal(true);
    check(quote.useSingleQuoteSignal() == true,
          "3.1 AlkOnlineQuote constructed, setUseSingleQuoteSignal(true) readback");
    quote.setUseSingleQuoteSignal(false);
    check(quote.useSingleQuoteSignal() == false,
          "3.2 single-quote signal toggle back to false");

    // 3.3 未知报价源名的 launch 走 initSource 失败路径：返回 false 且不发起
    //     任何下载（消费者可见的错误契约）
    bool launched = quote.launch(QString::fromLatin1("ALKIMIA"),
                                 QString::fromLatin1("ALK"),
                                 QString::fromLatin1("no-such-source"));
    check(launched == false,
          "3.3 launch() with unknown source returns false (no download)");
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    Q_UNUSED(app);

    std::printf("libalkimia consumer e2e (package libalkimia/8.2.1)\n");
    case1_value_roundtrip();
    case2_quotesource_store_roundtrip();
    case3_quote_engine_consumer_contract();

    std::printf("RESULT: %d checks, %d failures\n", g_checks, g_failures);
    if (g_failures == 0) {
        std::printf("ALL_CONSUMER_TESTS_PASSED\n");
        return 0;
    }
    return 1;
}
