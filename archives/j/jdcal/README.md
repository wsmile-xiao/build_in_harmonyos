# jdcal

`jdcal` 1.4.1 is a pure-Python module for converting dates between the Julian
and proleptic Gregorian calendars. Upstream: https://github.com/phn/jdcal

## OpenHarmony PC package

The Conan recipe packages the upstream `jdcal.py` module and its BSD license.
It exposes the module through `PYTHONPATH`; no native compilation or runtime
dependency is required. Source archive URL and SHA-256 are fixed in
`1.4.1/conandata.yml`.

The contest task #7593 is labelled `cpp`, while the fixed upstream source is
Python. The task label has not been changed, and language eligibility or points
have not been confirmed. See the version notes and test report for the exact
validation scope and outstanding failures.
