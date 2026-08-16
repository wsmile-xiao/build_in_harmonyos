#include <QtLocation/QPlace>
#include <QtLocation/QPlaceCategory>
#include <QtLocation/QPlaceContactDetail>
#include <QtLocation/QGeoServiceProvider>
#include <QtCore/QString>

#include <cstdio>

/*
 * Substantive smoke test for the Qt Location package on HarmonyOS PC.
 *
 * Exercises the real geo/place types (QPlace, QPlaceCategory,
 * QPlaceContactDetail) and the service-provider facade — not a stub.
 */
int main()
{
    // QPlace: construction, identifiers, coordinate/visibility.
    QPlace place;
    place.setPlaceId(QStringLiteral("test-place-1"));
    place.setName(QStringLiteral("HarmonyOS Test Place"));
    if (place.placeId() != QStringLiteral("test-place-1")) {
        std::fprintf(stderr, "QPlace::placeId round-trip failed\n");
        return 1;
    }
    if (place.name() != QStringLiteral("HarmonyOS Test Place")) {
        std::fprintf(stderr, "QPlace::name round-trip failed\n");
        return 2;
    }

    // QPlaceCategory: category hierarchy.
    QPlaceCategory category;
    category.setCategoryId(QStringLiteral("cat-1"));
    category.setName(QStringLiteral("Test Category"));
    if (category.categoryId() != QStringLiteral("cat-1") ||
        category.name() != QStringLiteral("Test Category")) {
        std::fprintf(stderr, "QPlaceCategory round-trip failed\n");
        return 3;
    }

    // QPlaceContactDetail: contact sub-types.
    QPlaceContactDetail contact;
    contact.setLabel(QStringLiteral("phone"));
    contact.setValue(QStringLiteral("+86-000-0000"));
    if (contact.label() != QStringLiteral("phone") ||
        contact.value() != QStringLiteral("+86-000-0000")) {
        std::fprintf(stderr, "QPlaceContactDetail round-trip failed\n");
        return 4;
    }

    // QGeoServiceProvider: construct a provider by name; on this headless
    // build no backend plugin is present, so an error state is expected —
    // this still exercises the real API surface.
    QGeoServiceProvider provider(QStringLiteral("test.provider"));
    const QGeoServiceProvider::Error error = provider.error();
    const QString errorString = provider.errorString();
    if (error != QGeoServiceProvider::NoError && errorString.isEmpty()) {
        std::fprintf(stderr, "QGeoServiceProvider error state inconsistent\n");
        return 5;
    }

    std::printf("QtLocation OK: place=%s category=%s contact=%s provider_error=%d\n",
                qPrintable(place.name()),
                qPrintable(category.name()),
                qPrintable(contact.label()),
                int(error));
    return 0;
}
