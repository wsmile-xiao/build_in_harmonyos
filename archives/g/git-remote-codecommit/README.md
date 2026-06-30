# git-remote-codecommit

Git remote helper for AWS CodeCommit — simplifies pushing to and pulling from CodeCommit repositories.

## Version 1.17

- **Build System**: pip (Python package)
- **License**: Apache License 2.0
- **URL**: https://github.com/aws/git-remote-codecommit

## Runtime Dependencies

- botocore >= 1.17.0

## Build Notes

This is a pure Python package installed via `pip install . --target` or `python3 setup.py install --prefix --root`.

Key adaptations for HarmonyOS:
- pip `--prefix` + `--root` conflict → use `setup.py install --prefix --root` for DESTDIR mode
- Console script must be manually created (easy_install .egg format not recognized by importlib.metadata)
- Python dependencies require Chinese PyPI mirror (pypi.tuna.tsinghua.edu.cn) for faster downloads