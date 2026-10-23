from urllib.parse import urlparse, urljoin
from collections import namedtuple

URLParts = namedtuple("URLParts", [
    "scheme", "host", "port", "path", "query", "username", "password"
])

DEFAULT_PORTS = {"http": 80, "https": 443}


def parse(url, base_url=None):
    if base_url:
        url = urljoin(base_url, url)

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError("Unsupported scheme '{}', only http/https allowed".format(scheme))

    host = parsed.hostname
    if not host:
        raise ValueError("No hostname found in URL: {}".format(url))

    if parsed.port is not None:
        port = parsed.port
    else:
        port = DEFAULT_PORTS[scheme]

    path = parsed.path if parsed.path else "/"
    query = parsed.query

    username = parsed.username
    password = parsed.password

    return URLParts(
        scheme=scheme,
        host=host,
        port=port,
        path=path,
        query=query,
        username=username,
        password=password,
    )


def build_url(url_parts):
    path = url_parts.path
    if url_parts.query:
        path = "{}?{}".format(path, url_parts.query)

    if url_parts.port == DEFAULT_PORTS[url_parts.scheme]:
        host_str = url_parts.host
    else:
        host_str = "{}:{}".format(url_parts.host, url_parts.port)

    return "{}://{}{}".format(url_parts.scheme, host_str, path)


if __name__ == "__main__":
    tests = [
        ("http://example.com", None,
         URLParts("http", "example.com", 80, "/", "", None, None)),
        ("https://example.com:8443/path", None,
         URLParts("https", "example.com", 8443, "/path", "", None, None)),
        ("http://user:pass@example.com/q?q=1#frag", None,
         URLParts("http", "example.com", 80, "/q", "q=1", "user", "pass")),
        ("http://example.com", None,
         URLParts("http", "example.com", 80, "/", "", None, None)),
        ("/new/path", "http://example.com:8080/old/path",
         URLParts("http", "example.com", 8080, "/new/path", "", None, None)),
    ]

    all_pass = True
    for url, base, expected in tests:
        result = parse(url, base_url=base)
        if result != expected:
            print("FAIL: parse('{}', base='{}')".format(url, base))
            print("  expected: {}".format(expected))
            print("  got:      {}".format(result))
            all_pass = False
        else:
            print("OK:   parse('{}') -> {}".format(url, result))

    if all_pass:
        print("\nAll tests passed.")
    else:
        print("\nSome tests failed.")
