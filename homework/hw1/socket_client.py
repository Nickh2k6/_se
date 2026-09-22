import socket
import ssl
import sys
from utils import debug_print

RECV_BUF_SIZE = 8192


class ConnectionError(Exception):
    pass


class DNSResolutionError(ConnectionError):
    pass


class ConnectionRefusedError(ConnectionError):
    pass


class TimeoutError(ConnectionError):
    pass


class Connection:
    def __init__(self):
        self._sock = None
        self._ssl_sock = None

    def connect(self, host, port, timeout=None, use_ssl=False):
        try:
            addrinfos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror as e:
            raise DNSResolutionError("Could not resolve host '{}': {}".format(host, e))

        if not addrinfos:
            raise DNSResolutionError("Could not resolve host: {}".format(host))

        last_error = None
        for family, socktype, proto, canonname, sockaddr in addrinfos:
            try:
                sock = socket.socket(family, socktype, proto)
                if timeout is not None:
                    sock.settimeout(timeout)
                debug_print("Trying {}:{}...".format(sockaddr[0], sockaddr[1]))
                sock.connect(sockaddr)
                self._sock = sock
                break
            except socket.timeout as e:
                last_error = TimeoutError("Connection to {}:{} timed out".format(host, port))
                sock.close()
            except OSError as e:
                last_error = ConnectionRefusedError(
                    "Cannot connect to {}:{} - {}".format(host, port, e))
                sock.close()

        if self._sock is None:
            if last_error:
                raise last_error
            raise ConnectionError("Failed to connect to {}:{}".format(host, port))

        if use_ssl:
            ctx = ssl.create_default_context()
            try:
                self._ssl_sock = ctx.wrap_socket(self._sock, server_hostname=host)
            except ssl.SSLError as e:
                self.close()
                raise ConnectionError("SSL handshake failed: {}".format(e))

        debug_print("Connected to {}:{}".format(host, port))

    def send(self, data):
        sock = self._ssl_sock or self._sock
        sock.sendall(data)
        debug_print("Sent {} bytes".format(len(data)))

    def receive(self, content_length=None, timeout=None, on_progress=None):
        sock = self._ssl_sock or self._sock
        if timeout is not None:
            sock.settimeout(timeout)

        chunks = []
        received = 0

        try:
            while True:
                if content_length is not None and received >= content_length:
                    break

                try:
                    chunk = sock.recv(RECV_BUF_SIZE)
                except socket.timeout:
                    raise TimeoutError("Receive timed out")

                if not chunk:
                    break

                chunks.append(chunk)
                received += len(chunk)

                if on_progress:
                    on_progress(received, content_length)
        except OSError as e:
            if chunks:
                debug_print("Read error after {} bytes: {}".format(received, e))
            else:
                raise ConnectionError("Receive failed: {}".format(e))

        data = b"".join(chunks)
        debug_print("Received {} bytes total".format(len(data)))
        return data

    def close(self):
        if self._ssl_sock:
            try:
                self._ssl_sock.close()
            except OSError:
                pass
            self._ssl_sock = None
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


if __name__ == "__main__":
    import utils
    utils.set_verbose(True)

    print("=== Test: HTTP GET httpbin.org ===")
    try:
        conn = Connection()
        conn.connect("httpbin.org", 80, timeout=5)
        conn.send(b"GET /ip HTTP/1.1\r\nHost: httpbin.org\r\nConnection: close\r\n\r\n")
        resp = conn.receive(timeout=5)
        print(resp.decode("utf-8", errors="replace"))
        conn.close()
    except Exception as e:
        print("Error: {}".format(e))

    print("=== Test: HTTPS GET httpbin.org ===")
    try:
        conn = Connection()
        conn.connect("httpbin.org", 443, timeout=5, use_ssl=True)
        conn.send(b"GET /ip HTTP/1.1\r\nHost: httpbin.org\r\nConnection: close\r\n\r\n")
        resp = conn.receive(timeout=5)
        print(resp.decode("utf-8", errors="replace"))
        conn.close()
    except Exception as e:
        print("Error: {}".format(e))
