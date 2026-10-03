# Direct Dependency License Summary

Source: the direct dependency declarations in `pyproject.toml`, reviewed 2026-10-03. The project itself is licensed under the MIT License; see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

This page records the declared direct runtime, build, and development dependencies and their listed upstream license identifiers. It does not enumerate transitive dependencies, verify every distributed artifact, or certify legal compliance. Check the license file for the exact dependency version used in a distribution.

## Direct dependencies

| Scope | Package | Declared constraint | Recorded license | Upstream license information |
|:--|:--|:--|:--|:--|
| Runtime | `psutil` | `>=7.2,<8` | BSD-3-Clause | [psutil license](https://github.com/giampaolo/psutil/blob/master/LICENSE) |
| Build backend | `hatchling` | `>=1.24` | MIT | [Hatch license](https://github.com/pypa/hatch/blob/master/LICENSE.txt) |
| Development | `pytest` | `>=9.1.1` | MIT | [pytest license](https://github.com/pytest-dev/pytest/blob/main/LICENSE) |
| Development | `ruff` | `>=0.5.0` | MIT | [Ruff license](https://github.com/astral-sh/ruff/blob/main/LICENSE) |

The Python standard library is supplied with the selected Python interpreter; it is not a separately declared third-party project dependency in `pyproject.toml` and is not included in this list. The list is limited to direct declarations and does not establish the licenses of their transitive dependencies.
