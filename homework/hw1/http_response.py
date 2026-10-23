from collections import namedtuple
from utils import debug_print

Response = namedtuple("Response", [
    "status_code", "reason", "headers", "body", "raw_head"
])

NO_BODY_STATUS_CODES = frozenset([100, 101, 204, 304])


def parse(raw_bytes):
    separator = b"\r\n\r\n"
    sep_pos = raw_bytes.find(separator)

    if sep_pos == -1:
        return Response(
            status_code=0,
            reason="Incomplete response",
            headers={},
            body=raw_bytes,
            raw_head=b""
        )

    head = raw_bytes[:sep_pos]
    body = raw_bytes[sep_pos + len(separator):]

    head_str = head.decode("latin-1")
    lines = head_str.split("\r\n")

    status_code, reason, headers = _parse_head(lines)

    if status_code in NO_BODY_STATUS_CODES:
        body = b""
    elif "transfer-encoding" in headers and headers["transfer-encoding"] == "chunked":
        body = _decode_chunked(body)
    elif "content-length" in headers:
        cl = int(headers["content-length"])
        body = body[:cl]

    return Response(
        status_code=status_code,
        reason=reason,
        headers=headers,
        body=body,
        raw_head=head
    )


def _parse_head(lines):
    status_line = lines[0]
    parts = status_line.split(" ", 2)

    if len(parts) < 2:
        raise ValueError("Malformed status line: {}".format(status_line))

    try:
        status_code = int(parts[1])
    except ValueError:
        raise ValueError("Invalid status code: {}".format(parts[1]))

    reason = parts[2] if len(parts) > 2 else ""

    headers = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    return status_code, reason, headers


def _decode_chunked(raw):
    chunks = []
    pos = 0

    while pos < len(raw):
        line_end = raw.find(b"\r\n", pos)
        if line_end == -1:
            break

        chunk_line = raw[pos:line_end].decode("latin-1")

        size_str = chunk_line.split(";")[0].strip()
        try:
            chunk_size = int(size_str, 16)
        except ValueError:
            debug_print("Malformed chunk size: {}".format(size_str))
            break

        if chunk_size == 0:
            break

        data_start = line_end + 2
        data_end = data_start + chunk_size
        chunks.append(raw[data_start:data_end])

        pos = data_end + 2

    return b"".join(chunks)


def has_body(response, method="GET"):
    if response.status_code in NO_BODY_STATUS_CODES:
        return False
    if method.upper() == "HEAD":
        return False
    if "content-length" in response.headers:
        return int(response.headers["content-length"]) > 0
    if "transfer-encoding" in response.headers:
        return True
    if "connection" in response.headers and response.headers["connection"] == "close":
        return True
    return True


def get_content_length(response):
    if "content-length" in response.headers:
        return int(response.headers["content-length"])
    return None


def is_redirect(response):
    return 300 <= response.status_code < 400


def get_redirect_url(response):
    return response.headers.get("location", None)


def is_connection_close(response):
    return response.headers.get("connection", "").lower() == "close"


if __name__ == "__main__":
    print("=== Test 1: Simple response ===")
    raw = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/plain\r\n"
        b"Content-Length: 5\r\n"
        b"\r\n"
        b"hello"
    )
    resp = parse(raw)
    print("Status:", resp.status_code, resp.reason)
    print("Headers:", resp.headers)
    print("Body:", repr(resp.body))
    assert resp.status_code == 200
    assert resp.body == b"hello"
    print("PASS\n")

    print("=== Test 2: Chunked response ===")
    raw = (
        b"HTTP/1.1 200 OK\r\n"
        b"Transfer-Encoding: chunked\r\n"
        b"\r\n"
        b"5\r\n"
        b"hello\r\n"
        b"6\r\n"
        b" world\r\n"
        b"0\r\n"
        b"\r\n"
    )
    resp = parse(raw)
    print("Status:", resp.status_code)
    print("Body:", repr(resp.body))
    assert resp.body == b"hello world"
    print("PASS\n")

    print("=== Test 3: No body (204) ===")
    raw = (
        b"HTTP/1.1 204 No Content\r\n"
        b"\r\n"
    )
    resp = parse(raw)
    print("Status:", resp.status_code)
    print("Body:", repr(resp.body))
    assert resp.body == b""
    print("PASS\n")

    print("=== Test 4: Incomplete response ===")
    raw = b"HTTP/1.1 200 OK\r\nContent-Type"
    resp = parse(raw)
    print("Status:", resp.status_code)
    assert resp.status_code == 0
    print("PASS\n")

    print("=== Test 5: Case-insensitive headers ===")
    raw = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/html\r\n"
        b"X-Custom-Header: value\r\n"
        b"\r\n"
    )
    resp = parse(raw)
    assert "content-type" in resp.headers
    assert "x-custom-header" in resp.headers
    print("PASS\n")

    print("All tests passed.")
