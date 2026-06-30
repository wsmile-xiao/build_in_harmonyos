# s3cmd

S3cmd is a command line tool for managing Amazon S3 and CloudFront services.
It allows uploading, retrieving, and managing data in Amazon S3 using simple
command line commands. Supports rsync-like backup, GPG encryption, and more.

## Version

- 2.4.0 (published)

## Dependencies

- python-dateutil (runtime)
- python-magic (runtime)

## OHOS Adaptation

- s3cmd is a pure Python project, no C/C++ compilation required
- Install method: `pip install --prefix=$DEFAULT_PREFIX --root=$TEST_PREFIX --no-deps`
- OHOS-specific modification: sys.path.insert to add site-packages path (Python interpreter doesn't search $DEFAULT_PREFIX site-packages by default)
- Patch: 0001-s3cmd.patch (platform adaptation for sys.path)

## Notes

- s3cmd requires python-dateutil and python-magic to be pre-installed
- The sys.path adaptation is required because harmonybrew Python doesn't search $DEFAULT_PREFIX/lib/pythonX.Y/site-packages/
- This is a known pattern for Python projects on OHOS (E080)