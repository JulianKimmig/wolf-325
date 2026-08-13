# Home Assistant development workflow

## Supported local environment

The locked integration harness is
`pytest-homeassistant-custom-component==0.13.316`, matching Home Assistant
2026.2.3 on Python 3.13.2 or newer within the Python 3.13 line. The uv `dev`
group declares that narrower interpreter range; published client metadata
remains Python 3.11+.

## Commands

Run the baseline harness:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest -c tests/components/wolf_cwl2/pytest.toml tests/components/wolf_cwl2/test_harness.py -q
```

Run all Home Assistant component tests:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest \
  -c tests/components/wolf_cwl2/pytest.toml \
  -p no:sugar -q --tb=short --log-level=CRITICAL \
  tests/components/wolf_cwl2
```

Run the client/CLI/TUI regression suite with the Home Assistant plugin isolated:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest \
  -p no:sugar -q --ignore=tests/components
```

A complete validation run executes both the client command and the HA command.
The separate pytest configurations are intentional: the extracted Home
Assistant plugin installs host-wide event-loop and cleanup fixtures designed
for Core-shaped tests, so it must not alter the standalone client suite. Keep
the explicit HA test path: the extracted plugin rewrites generic discovery for
compatibility with the Home Assistant Core test layout.

Validate whitespace and source size before a closed commit:

```bash
git diff --check
find src custom_components -name '*.py' -print0 | xargs -0 awk 'FNR == 1 { file = FILENAME } { count[FILENAME]++ } END { for (file in count) if (count[file] > 300) print file, count[file] }'
```

The Home Assistant fixture is an external host boundary. Component tests may
fake the gateway/Modbus client, but must exercise real integration runtime,
Store adapters, client validation, profile algorithms, config flows, entities,
and action handlers. Source controller methods are not mocked.

## TDD sequence

1. Add behavior tests under `tests/components/wolf_cwl2/` and observe the
   expected failure.
2. Implement the smallest cohesive integration modules under
   `custom_components/wolf_cwl2/`.
3. Run the focused component test, then the complete component suite.
4. Run the full repository suite and update the owning system-of-record files.
5. Check source files remain below 300 lines and commit the closed slice.

Clean artifact installation, HACS metadata, publication blockers, and the
current external-rule review are owned by the
[release validation workflow](home-assistant-release-validation.md). Hassfest,
public HACS validation, and end-user installation remain release gates until
the approved public metadata and exact published client dependency exist.
