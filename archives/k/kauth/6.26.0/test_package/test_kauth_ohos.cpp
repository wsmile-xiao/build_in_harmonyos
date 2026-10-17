#include <KAuth/Action>
#include <KAuth/ActionReply>
#include <KAuth/ExecuteJob>
#include <QCoreApplication>
#include <QString>
#include <cstdio>

// HarmonyOS-specific test of the kauth platform adaptation path (R40/R34).
//
// OHOS has no Polkit and no D-Bus session daemon, so the recipe builds kauth
// with KAUTH_BACKEND_NAME=FAKE (see conanfile.py generate() and notes.md).
// With no backend plugin present in KAUTH_BACKEND_PLUGIN_DIR,
// BackendsManager::init() falls back to a plain FakeBackend, which reports
// KAuth::AuthBackend::NoCapability. This test asserts the exact observable
// behavior of that platform adaptation path rather than merely linking the
// library:
//
//   1. Action(name).isValid() == true and name() round-trips; the default
//      Action().isValid() == false (isValid() is purely the "name set" test).
//   2. An action with no name reports Action::InvalidStatus, while a named
//      action on the FAKE backend always reports Action::DeniedStatus
//      (FakeBackend::actionStatus() unconditionally returns DeniedStatus).
//   3. execute() on the FAKE backend cannot authorize: because the backend
//      advertises NoCapability, ExecuteJob falls into its else branch and
//      fails with ActionReply::BackendError and errorDescription
//      "The backend does not specify how to authorize". This is the FAKE
//      backend contract, not a defect - it is exactly why kauth cannot
//      authorize on OHOS.
//   4. No helper is bound (helperId() empty, hasHelper() == false), since
//      KAUTH_HELPER_BACKEND_NAME=FAKE and no helper service exists.
//   5. setDetailsV2()/detailsV2() round-trip through the DetailsMap
//      (KAuth::Action::AuthDetail -> QVariant).
//
// Each assertion calls into real KF6::AuthCore API surface; the test returns a
// non-zero exit code on any mismatch, so it is a real gate on the OHOS
// adaptation behavior. It needs only QCoreApplication - no session bus, no
// Polkit, no Qt platform plugin.

// This is a HarmonyOS-specific test: compiling it for a non-OHOS target would
// make it meaningless (the FAKE backend is an OHOS adaptation choice), so fail
// loudly instead of silently producing a host-side "pass".
#ifndef __OHOS__
#  error "test_kauth_ohos is a HarmonyOS-specific test; build it for OHOS only"
#endif

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    bool ok = true;

    // 1) name() / isValid() semantics.
    KAuth::Action action(QStringLiteral("org.kde.kauth.ohos.test"));
    std::printf("[ohos] name()='%s' (expect org.kde.kauth.ohos.test)\n",
                qPrintable(action.name()));
    if (action.name() != QStringLiteral("org.kde.kauth.ohos.test")) {
        std::printf("[ohos] FAIL: name() round-trip mismatch\n");
        ok = false;
    }
    if (!action.isValid()) {
        std::printf("[ohos] FAIL: expected isValid()==true for a named action\n");
        ok = false;
    }

    KAuth::Action unnamed;
    std::printf("[ohos] unnamed.isValid()=%d (expect 0)\n", unnamed.isValid() ? 1 : 0);
    if (unnamed.isValid()) {
        std::printf("[ohos] FAIL: expected isValid()==false for a nameless action\n");
        ok = false;
    }

    // 2) status() on the FAKE backend.
    const int unnamedStatus = static_cast<int>(unnamed.status());
    std::printf("[ohos] unnamed.status()=%d (expect 2=InvalidStatus)\n", unnamedStatus);
    if (unnamedStatus != static_cast<int>(KAuth::Action::InvalidStatus)) {
        std::printf("[ohos] FAIL: expected InvalidStatus for a nameless action\n");
        ok = false;
    }

    const int namedStatus = static_cast<int>(action.status());
    std::printf("[ohos] named.status()=%d (expect 0=DeniedStatus, FAKE backend)\n", namedStatus);
    if (namedStatus != static_cast<int>(KAuth::Action::DeniedStatus)) {
        std::printf("[ohos] FAIL: expected DeniedStatus from the FAKE backend\n");
        ok = false;
    }

    // 3) execute() on the FAKE backend must fail with BackendError.
    KAuth::ExecuteJob *job = action.execute();
    if (!job) {
        std::printf("[ohos] FAIL: execute() returned a null job\n");
        ok = false;
    } else {
        const bool returned = job->exec();
        std::printf("[ohos] job->exec()=%d (expect 0: FAKE backend cannot authorize)\n",
                    returned ? 1 : 0);
        if (returned) {
            std::printf("[ohos] FAIL: expected execute() to fail on the FAKE backend\n");
            ok = false;
        }

        const int jobError = job->error();
        std::printf("[ohos] job->error()=%d (expect %d=BackendError)\n",
                    jobError, static_cast<int>(KAuth::ActionReply::BackendError));
        if (jobError != static_cast<int>(KAuth::ActionReply::BackendError)) {
            std::printf("[ohos] FAIL: expected ActionReply::BackendError\n");
            ok = false;
        }

        const QString errorString = job->errorString();
        std::printf("[ohos] job->errorString()='%s'\n", qPrintable(errorString));
        if (!errorString.contains(QStringLiteral("does not specify how to authorize"))) {
            std::printf("[ohos] FAIL: unexpected backend error description\n");
            ok = false;
        }
    }

    // 4) No helper backend on OHOS.
    std::printf("[ohos] helperId().isEmpty()=%d (expect 1)\n",
                action.helperId().isEmpty() ? 1 : 0);
    if (!action.helperId().isEmpty()) {
        std::printf("[ohos] FAIL: expected no helper id\n");
        ok = false;
    }
    std::printf("[ohos] hasHelper()=%d (expect 0)\n", action.hasHelper() ? 1 : 0);
    if (action.hasHelper()) {
        std::printf("[ohos] FAIL: expected hasHelper()==false\n");
        ok = false;
    }

    // 5) setDetailsV2()/detailsV2() round-trip.
    KAuth::Action::DetailsMap details;
    details.insert(KAuth::Action::AuthDetail::DetailMessage, QStringLiteral("kauth-ohos"));
    action.setDetailsV2(details);
    const KAuth::Action::DetailsMap readBack = action.detailsV2();
    std::printf("[ohos] detailsV2().size()=%d (expect 1)\n", static_cast<int>(readBack.size()));
    if (readBack.size() != 1) {
        std::printf("[ohos] FAIL: expected one detail entry after setDetailsV2()\n");
        ok = false;
    }
    const QString message =
        readBack.value(KAuth::Action::AuthDetail::DetailMessage).toString();
    std::printf("[ohos] DetailMessage='%s' (expect kauth-ohos)\n", qPrintable(message));
    if (message != QStringLiteral("kauth-ohos")) {
        std::printf("[ohos] FAIL: detail round-trip mismatch\n");
        ok = false;
    }

    std::printf("test_kauth_ohos: %s\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}
