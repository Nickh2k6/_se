from utils import debug_print

DEFAULT_USER_AGENT = "mycurl/1.0"


def build(method, url_parts, user_headers=None, body=None, content_type=None):
    headers = {}

    path = url_parts.path
    if url_parts.query:
        path = "{}?{}".format(path, url_parts.query)

    headers["Host"] = url_parts.host
    if url_parts.port not in (80, 443):
        headers["Host"] = "{}:{}".format(url_parts.host, url_parts.port)

    headers["User-Agent"] = DEFAULT_USER_AGENT
    headers["Connection"] = "close"

    if body is not None:
        if isinstance(body, str):
            body = body.encode("utf-8")
        headers["Content-Length"] = str(len(body))
        if content_type is None and method.upper() != "GET":
            content_type = "application/x-www-form-urlencoded"
        if content_type:
            headers["Content-Type"] = content_type

    if user_headers:
        for key, value in user_headers:
            headers[key] = value

    request_line = "{} {} HTTP/1.1\r\n".format(method.upper(), path)
    header_lines = "".join(
        "{}: {}\r\n".format(k, v) for k, v in headers.items()
    )
    request = request_line + header_lines + "\r\n"

    if body is not None:
        request = request.encode("latin-1") + body
    else:
        request = request.encode("latin-1")

    debug_print("--- Request ---")
    debug_print(request.decode("latin-1", errors="replace"))
    debug_print("---------------")

    return request


def build_basic_auth_header(username, password):
    import base64
    credentials = "{}:{}".format(username, password)
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
    return ("Authorization", "Basic {}".format(encoded))


if __name__ == "__main__":
    from collections import namedtuple
    from url_parser import URLParts

    fake = URLParts("http", "example.com", 80, "/api/test", "q=1", None, None)

    req = build("GET", fake)
    print("GET request:")
    print(repr(req))
    print()

    req = build("POST", fake, body="name=alice&age=20")
    print("POST request:")
    print(repr(req))
    print()

    req = build("PUT", fake, body=b"\x00\x01\x02", content_type="application/octet-stream")
    print("PUT binary request:")
    print(repr(req))
    print()

    req = build("GET", fake, user_headers=[("Accept", "text/html")])
    print("GET with custom header:")
    print(repr(req))
