import sys

VERBOSE = False


def set_verbose(enabled):
    global VERBOSE
    VERBOSE = enabled


def debug_print(msg):
    if VERBOSE:
        print(msg, file=sys.stderr)


def escape_bytes(data):
    result = []
    for b in data:
        if b == 0x5c:
            result.append("\\\\")
        elif b == 0x0d:
            result.append("\\r")
        elif b == 0x0a:
            result.append("\\n")
        elif b == 0x09:
            result.append("\\t")
        elif 0x20 <= b <= 0x7e:
            result.append(chr(b))
        else:
            result.append("\\x{:02x}".format(b))
    return "".join(result)
