"""Execution requirements; importing and displaying help need no POSIX APIs."""

import os
import sys

from .errors import WikiError


DIR_FD_FUNCTIONS = (os.open, os.mkdir, os.stat, os.unlink, os.rename)
STAT = os.stat
ENUMERATION = (os.listdir, os.scandir)


def require_capabilities():
    missing = []
    if not (sys.platform == 'darwin' or sys.platform.startswith('linux')):
        missing.append('macOS or Linux')
    for name in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK', 'O_CLOEXEC',
                 'pread', 'fsync', 'fstat', 'set_inheritable', 'open', 'mkdir', 'stat',
                 'unlink', 'replace', 'listdir', 'scandir', 'dup', 'close', 'write', 'fdopen'):
        if not hasattr(os, name):
            missing.append('os.' + name)
    for function in DIR_FD_FUNCTIONS:
        if function not in os.supports_dir_fd:
            missing.append(function.__name__ + '(dir_fd)')
    if STAT not in os.supports_follow_symlinks:
        missing.append('stat(follow_symlinks=False)')
    if any(function not in os.supports_fd for function in ENUMERATION):
        missing.append('directory descriptor enumeration')
    try:
        import fcntl
        if not all(hasattr(fcntl, name) for name in ('flock', 'LOCK_SH', 'LOCK_EX', 'LOCK_NB')):
            missing.append('native flock')
    except ImportError:
        missing.append('native flock')
    if missing:
        raise WikiError('Unsupported platform/capabilities: ' + ', '.join(missing)
                        + '; execution requires local macOS/Linux POSIX file access and native flock',
                        'unsupported_platform')
