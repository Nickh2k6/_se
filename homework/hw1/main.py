import argparse
import sys
from url_parser import parse as parse_url
from http_request import build as build_request, build_basic_auth_header
from http_response import (
    parse as parse_response, is_redirect, get_redirect_url
)
from socket_client import Connection, ConnectionError as ConnError, TimeoutError, DNSResolutionError
from utils import set_verbose, debug_print, escape_bytes

MAX_REDIRECTS = 20
PROGRESS_WIDTH = 40


def parse_args():
    p = argparse.ArgumentParser(
        prog="mycurl",
        description="A curl-like HTTP client"
    )
    p.add_argument("urls", nargs="+", help="URL(s) to fetch")
    p.add_argument("-X", "--request", default="GET",
                   help="HTTP method (default: GET)")
    p.add_argument("-H", "--header", action="append", default=[],
                   metavar="NAME:VALUE",
                   help="Custom header (repeatable)")
    p.add_argument("-d", "--data", default=None,
                   help="Request body (string or @filename)")
    p.add_argument("-o", "--output", default=None,
                   help="Write body to file")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Verbose output")
    p.add_argument("-L", "--location", action="store_true",
                   help="Follow redirects")
    p.add_argument("-m", "--max-time", type=float, default=None,
                   help="Timeout in seconds")
    p.add_argument("--user", default=None,
                   help="user:password for Basic auth")
    p.add_argument("--no-progress", action="store_true",
                   help="Disable progress bar")
    return p.parse_args()


def parse_headers(header_list):
    headers = []
    for h in header_list:
        if ":" not in h:
            print("Error: malformed header '{}' (use NAME:VALUE)".format(h),
                  file=sys.stderr)
            sys.exit(6)
        key, value = h.split(":", 1)
        headers.append((key.strip(), value.strip()))
    return headers


def read_body_data(data_arg):
    if data_arg is None:
        return None
    if data_arg.startswith("@"):
        filepath = data_arg[1:]
        try:
            with open(filepath, "rb") as f:
                return f.read()
        except IOError as e:
            print("Error: cannot read '{}': {}".format(filepath, e),
                  file=sys.stderr)
            sys.exit(6)
    return data_arg.encode("utf-8")


def extract_url_auth(url_parts):
    username = url_parts.username
    password = url_parts.password or ""
    return username, password


def show_progress(received, total):
    if total is not None and total > 0:
        pct = min(received / total, 1.0)
        filled = int(PROGRESS_WIDTH * pct)
        bar = "=" * filled + "-" * (PROGRESS_WIDTH - filled)
        sys.stderr.write("\r[{}] {:.1f}% ({}/{})".format(
            bar, pct * 100, received, total))
    else:
        sys.stderr.write("\rReceived {} bytes".format(received))
    sys.stderr.flush()


def format_verbose_response(response, url):
    lines = []
    lines.append("< HTTP/1.1 {} {}".format(response.status_code, response.reason))
    for k, v in response.headers.items():
        lines.append("< {}: {}".format(k, v))
    return "\n".join(lines)


def do_request(url_str, method, headers, body, verbose, follow_redirects,
               timeout, auth_user, auth_pass, show_progress_bar, output_file):
    redirect_count = 0
    current_url = url_str
    current_method = method
    current_body = body

    while True:
        url_parts = parse_url(current_url)

        req_headers = list(headers)

        if auth_user is not None:
            req_headers.append(build_basic_auth_header(auth_user, auth_pass))

        request_bytes = build_request(
            current_method, url_parts,
            user_headers=req_headers,
            body=current_body
        )

        use_ssl = url_parts.scheme == "https"
        conn = Connection()
        try:
            conn.connect(url_parts.host, url_parts.port,
                        timeout=timeout, use_ssl=use_ssl)

            conn.send(request_bytes)

            cl = get_content_length_from_request(request_bytes)
            progress_cb = show_progress if show_progress_bar else None
            raw = conn.receive(content_length=cl, timeout=timeout,
                             on_progress=progress_cb)

        except DNSResolutionError as e:
            print("Error: {}".format(e), file=sys.stderr)
            return 6
        except TimeoutError as e:
            print("Error: {}".format(e), file=sys.stderr)
            return 28
        except ConnError as e:
            print("Error: {}".format(e), file=sys.stderr)
            return 7
        finally:
            conn.close()

        if show_progress_bar:
            sys.stderr.write("\n")
            sys.stderr.flush()

        response = parse_response(raw)

        if verbose:
            debug_print(format_verbose_response(response, current_url))
            debug_print("")

        if is_redirect(response) and follow_redirects:
            location = get_redirect_url(response)
            if not location:
                print("Error: {} redirect but no Location header".format(
                    response.status_code), file=sys.stderr)
                return 3

            current_url = location
            if response.status_code in (301, 302, 303):
                current_method = "GET"
                current_body = None
            redirect_count += 1
            if redirect_count > MAX_REDIRECTS:
                print("Error: too many redirects ({})".format(redirect_count),
                      file=sys.stderr)
                return 3
            debug_print("Redirecting to {} ({})".format(
                current_url, response.status_code))
            continue

        if output_file:
            with open(output_file, "wb") as f:
                f.write(response.body)
        else:
            sys.stdout.buffer.write(response.body)

        return 0


def get_content_length_from_request(request_bytes):
    try:
        head = request_bytes.split(b"\r\n\r\n")[0].decode("latin-1")
        for line in head.split("\r\n"):
            if line.lower().startswith("content-length:"):
                return int(line.split(":", 1)[1].strip())
    except (ValueError, IndexError):
        pass
    return None


def main():
    args = parse_args()
    set_verbose(args.verbose)

    method = args.request
    headers = parse_headers(args.header)
    body = read_body_data(args.data)

    if body is not None and method == "GET":
        method = "POST"

    auth_user = None
    auth_pass = ""
    if args.user:
        if ":" in args.user:
            auth_user, auth_pass = args.user.split(":", 1)
        else:
            auth_user = args.user

    exit_code = 0
    for url in args.urls:
        try:
            url_parts = parse_url(url)
        except ValueError as e:
            print("Error: Invalid URL '{}': {}".format(url, e), file=sys.stderr)
            exit_code = 3
            continue

        if auth_user is None and url_parts.username:
            auth_user = url_parts.username
            auth_pass = url_parts.password or ""

        code = do_request(
            url, method, headers, body,
            verbose=args.verbose,
            follow_redirects=args.location,
            timeout=args.max_time,
            auth_user=auth_user,
            auth_pass=auth_pass,
            show_progress_bar=(not args.no_progress and args.output is not None),
            output_file=args.output
        )
        if code != 0:
            exit_code = code

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
