"""Stable opt-in failure codes; legacy messages remain available."""

import argparse
import errno
import json
import sys


GUIDANCE = {
    'invalid_input': 'correct_input', 'arguments': 'correct_input',
    'invalid_index': 'inspect_index', 'unsafe_path': 'inspect_paths',
    'not_found': 'inspect_inputs', 'already_exists': 'inspect_existing',
    'locked': 'wait_for_writer_or_inspect_lock', 'precondition_failed': 'reread_then_new_request',
    'request_conflict': 'restore_original_payload_or_use_new_request',
    'recovery_required': 'stop_and_inspect_request_and_bundle',
    'io_error': 'inspect_io_and_possible_partial_state',
    'internal_error': 'stop_and_inspect', 'concurrent_change': 'stop_and_inspect',
}


class WikiError(Exception):
    def __init__(self, message, code='invalid_input'):
        super().__init__(message)
        self.code = code


def error_code(exc):
    if isinstance(exc, WikiError):
        return exc.code
    if isinstance(exc, OSError):
        if exc.errno == errno.ENOENT:
            return 'not_found'
        if exc.errno == errno.EEXIST:
            return 'already_exists'
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            return 'unsafe_path'
        return 'io_error'
    if isinstance(exc, (ValueError, TypeError, UnicodeError)):
        return 'invalid_input'
    return 'internal_error'


def emit_error(exc):
    code = error_code(exc)
    # ASCII JSON also survives lone surrogates and strict UTF-8 stderr.
    message = str(exc)
    result = {'error': {'code': code, 'message': message[:1000],
                        'message_truncated': len(message) > 1000,
                        'action': GUIDANCE[code]}}
    print(json.dumps(result, ensure_ascii=True, allow_nan=False), file=sys.stderr)


class ErrorParser(argparse.ArgumentParser):
    def __init__(self, *args, machine=False, **kwargs):
        self.machine = machine
        super().__init__(*args, **kwargs)

    def error(self, message):
        if not self.machine:
            return super().error(message)
        emit_error(WikiError(message, 'arguments'))
        self.exit(2)


def machine_errors(argv):
    """Recognize the global mode before the command, including repeated options."""
    mode = 'legacy'
    commands = {'init', 'capture', 'curate', 'review', 'recall', 'search', 'list', 'show', 'history', 'diff', 'check', 'inspect-storage'}
    for index, arg in enumerate(argv):
        if arg in commands or arg == '--':
            break
        option, separator, value = arg.partition('=')
        if len(option) > 2 and '--error-format'.startswith(option):
            candidate = value if separator else (argv[index + 1] if index + 1 < len(argv) else None)
            if candidate in ('json', 'legacy'):
                mode = candidate
    return mode == 'json'
