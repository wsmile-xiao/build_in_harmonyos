// Consumer-side smoke test for libsignon-qt 8.61 (SignOnQt6).
//
// Exercises the public SignOn:: API actually exported by the packaged library:
// SignOn::Error (signonerror.h), SignOn::SessionData (sessiondata.h) and
// SignOn::IdentityInfo (identityinfo.h). Headers are included through the
// installed forwarding headers (<SignOn/...>), i.e. exactly the way
// kaccounts-integration consumes them. No D-Bus / signond daemon is required:
// only value-type APIs are used, so the test is meaningful in CI.
#include <QString>
#include <QStringList>
#include <QVariantMap>
#include <cstdio>

#include <SignOn/Error>
#include <SignOn/IdentityInfo>
#include <SignOn/SessionData>

static int failures = 0;

#define CHECK(cond, what)                                          \
    do {                                                           \
        if (!(cond)) {                                             \
            std::printf("FAIL: %s\n", what);                       \
            ++failures;                                            \
        } else {                                                   \
            std::printf("ok  : %s\n", what);                       \
        }                                                          \
    } while (0)

int main()
{
    // ---- SignOn::Error ----
    SignOn::Error err(SignOn::Error::InvalidCredentials, QStringLiteral("bad credentials"));
    CHECK(err.type() == SignOn::Error::InvalidCredentials, "Error(type,message) keeps the type");
    CHECK(err.message() == QStringLiteral("bad credentials"), "Error(type,message) keeps the message");
    err.setType(SignOn::Error::Network);
    err.setMessage(QStringLiteral("offline"));
    CHECK(err.type() == SignOn::Error::Network, "Error::setType");
    CHECK(err.message() == QStringLiteral("offline"), "Error::setMessage");

    SignOn::Error copy(err);
    CHECK(copy.type() == SignOn::Error::Network, "Error copy constructor");

    // ---- SignOn::SessionData ----
    SignOn::SessionData session;
    session.setUserName(QStringLiteral("alice"));
    session.setSecret(QStringLiteral("s3cret"));
    session.setUiPolicy(SignOn::RequestPasswordPolicy);
    session.setNetworkTimeout(1500);

    CHECK(session.UserName() == QStringLiteral("alice"), "SessionData::UserName");
    CHECK(session.Secret() == QStringLiteral("s3cret"), "SessionData::Secret");
    CHECK(session.UiPolicy() == SignOn::RequestPasswordPolicy, "SessionData::UiPolicy");
    CHECK(session.NetworkTimeout() == 1500, "SessionData::NetworkTimeout");
    CHECK(session.getProperty(QStringLiteral("UserName")).toString() == QStringLiteral("alice"),
          "SessionData::getProperty");

    const QVariantMap map = session.toMap();
    CHECK(map.size() == 4, "SessionData::toMap carries every property");

    SignOn::SessionData roundTrip(map);
    CHECK(roundTrip.Secret() == QStringLiteral("s3cret"), "SessionData round-trip through QVariantMap");
    CHECK(session.propertyNames().contains(QStringLiteral("UiPolicy")), "SessionData::propertyNames");

    // ---- SignOn::IdentityInfo ----
    SignOn::IdentityInfo info;
    info.setId(42);
    info.setUserName(QStringLiteral("bob"));
    info.setCaption(QStringLiteral("Bob's account"));
    info.setSecret(QStringLiteral("hunter2"), false);
    info.setRealms(QStringList() << QStringLiteral("https://example.org"));

    CHECK(info.id() == 42, "IdentityInfo::id");
    CHECK(info.userName() == QStringLiteral("bob"), "IdentityInfo::userName");
    CHECK(info.caption() == QStringLiteral("Bob's account"), "IdentityInfo::caption");
    CHECK(info.secret() == QStringLiteral("hunter2"), "IdentityInfo::secret");
    CHECK(!info.isStoringSecret(), "IdentityInfo::setSecret(storeSecret=false)");
    CHECK(info.realms().size() == 1, "IdentityInfo::realms");

    SignOn::IdentityInfo other;
    other = info;
    CHECK(other.userName() == QStringLiteral("bob"), "IdentityInfo assignment operator");

    if (failures != 0) {
        std::printf("test_libsignon_qt: %d check(s) FAILED\n", failures);
        return 1;
    }
    std::printf("test_libsignon_qt: all checks passed\n");
    return 0;
}
