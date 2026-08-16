<p align="center">
  <img src="logo.png" alt="Trendflow logo" width="280"/>
</p>

# Trendflow — Python API reference

Every class, method, and dataclass in [`trendflow-py`](https://pypi.org/project/trendflow-py/),
generated from the source docstrings on each commit.

**Looking for guides?** The full documentation — installation, usage, trending backends,
topics, proxies and rate limits — lives at
**[trendflow.mory.dev/docs/python](https://trendflow.mory.dev/docs/python)**, alongside the
[JavaScript documentation](https://trendflow.mory.dev/docs/js) and the
[hosted MCP server](https://trendflow.mory.dev/docs/mcp) for ChatGPT, Claude, and Cursor.

```bash
pip install trendflow-py
```

## On this site

- [API Reference](api.md) — every public symbol, generated from docstrings.
- [Architecture](architecture.md) — how the layers fit together: `_trends_http` holds the HTTP
  session, `_parsers` turns raw JSON into dataclasses, `_fetcher` provides the high-level
  `Client`, and `models` carries the results.

## Links

- Guides and canonical documentation: [trendflow.mory.dev](https://trendflow.mory.dev)
- Source: [github.com/dariomory/trendflow](https://github.com/dariomory/trendflow)
- Package: [pypi.org/project/trendflow-py](https://pypi.org/project/trendflow-py/)
- JavaScript sibling: [`trendflow`](https://www.npmjs.com/package/trendflow)
- MIT licensed, by [Dario Mory](https://mory.dev)
