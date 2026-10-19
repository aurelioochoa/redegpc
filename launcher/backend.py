"""Paths, preferences and bounded child IO; the Rust CLI owns game operations."""
from collections import deque
from dataclasses import dataclass
import math
import os
from pathlib import Path
import plistlib
import queue
import signal
import subprocess
import tempfile
import threading
from xml.parsers.expat import ExpatError


@dataclass(frozen=True)
class Directories:
    data: Path
    config: Path
    logs: Path

    @classmethod
    def discover(cls):
        home = Path(os.environ.get('HOME', ''))
        if not home.is_absolute():
            raise ValueError('HOME must be absolute')

        def base(key, fallback):
            path = Path(os.environ.get(key, ''))
            return (path if path.is_absolute() else home / fallback) / 'redegpc'

        return cls(base('XDG_DATA_HOME', '.local/share'),
                   base('XDG_CONFIG_HOME', '.config'),
                   base('XDG_STATE_HOME', '.local/state') / 'logs')


DEFAULTS = {'Fullscreen': False, 'TouchMode': False, 'Volume': 1.0}


def validate_settings(values):
    if not isinstance(values, dict) or values.keys() - DEFAULTS.keys():
        raise ValueError('Settings must contain only Fullscreen, TouchMode and Volume')
    result = {**DEFAULTS, **values}
    if any(type(result[key]) is not bool for key in ('Fullscreen', 'TouchMode')):
        raise ValueError('Display and input settings must be booleans')
    volume = result['Volume']
    if (type(volume) is not float or not math.isfinite(volume)
            or not 0 <= volume <= 1):
        raise ValueError('Volume must be a real number between 0 and 1')
    return result


def load_settings(dirs):
    path = dirs.config / 'settings.plist'
    if not path.exists():
        return dict(DEFAULTS)
    try:
        return validate_settings(plistlib.loads(path.read_bytes()))
    except ExpatError as error:
        raise ValueError(f'Invalid settings property list: {error}') from error


def save_settings(dirs, values):
    values = validate_settings(values)
    dirs.config.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.launcher-', dir=dirs.config)
    try:
        with os.fdopen(fd, 'wb') as stream:
            plistlib.dump(values, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, dirs.config / 'settings.plist')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def installation_present(dirs):
    """A pointer is a candidate only. `check` verifies all hashes in a child."""
    return (dirs.data / 'current.plist').is_file()


class Child:
    """Never block Tk on pipes, including long unterminated runtime output."""
    def __init__(self, command):
        self.process = subprocess.Popen(
            [str(arg) for arg in command], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, start_new_session=True, bufsize=0)
        self.output = queue.Queue(maxsize=128)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        import codecs
        decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        try:
            while chunk := self.process.stdout.read(4096):
                self._put(decoder.decode(chunk))
            self._put(decoder.decode(b'', final=True))
        finally:
            self.process.stdout.close()

    def _put(self, chunk):
        if not chunk:
            return
        try:
            self.output.put_nowait(chunk)
        except queue.Full:
            try:
                self.output.get_nowait()
            except queue.Empty:
                pass
            self.output.put_nowait(chunk)

    def poll(self):
        chunks = []
        while True:
            try:
                chunks.append(self.output.get_nowait())
            except queue.Empty:
                break
        code = self.process.poll()
        done = code is not None and not self.reader.is_alive() and self.output.empty()
        return ''.join(chunks), code if done else None

    def stop(self, force=False):
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL if force else signal.SIGTERM)
            except ProcessLookupError:
                pass


def tail_log(path, limit=65536):
    try:
        with path.open('rb') as stream:
            stream.seek(0, os.SEEK_END)
            stream.seek(max(0, stream.tell() - limit))
            return stream.read(limit).decode('utf-8', errors='replace')
    except FileNotFoundError:
        return 'No runtime log yet. Launch the game to create one.'


class Session:
    """Single-operation state shared by the UI and interaction checks."""
    def __init__(self, binary, dirs):
        self.binary, self.dirs = Path(binary), dirs
        self.child = None
        self.operation = None
        self.verified = False
        self.installation_error = None
        self.status = 'Checking installation…' if installation_present(dirs) else 'Import a game to begin'
        self.transcript = deque(maxlen=64)
        self.last_output = ''

    @property
    def installation_state(self):
        """Keep installation readiness separate from transient footer messages."""
        if self.operation in ('check', 'import', 'run'):
            return {'check': 'checking', 'import': 'importing', 'run': 'running'}[self.operation]
        if self.verified:
            return 'ready'
        if self.installation_error:
            return 'import_failed' if self.installation_error == 'import' else 'attention'
        return 'pending' if installation_present(self.dirs) else 'missing'

    def start(self, operation, *arguments):
        if self.child:
            return False
        self.child = Child([self.binary, operation, *arguments])
        self.operation = operation
        self.transcript.clear()
        self.last_output = ''
        self.status = {'check': 'Verifying installed files…',
                       'import': 'Importing game…',
                       'run': 'Game running'}.get(operation, operation)
        return True

    def tick(self):
        if not self.child:
            return None
        output, code = self.child.poll()
        if output:
            self.transcript.append(output[-8192:])
        if code is None:
            return None
        operation = self.operation
        self.last_output = ''.join(self.transcript)[-65536:]
        self.child, self.operation = None, None
        if operation in ('check', 'import'):
            self.verified = code == 0
            self.installation_error = operation if code else None
        if code:
            self.status = {'check': 'Installation needs attention',
                           'import': 'Import failed', 'run': 'Game exited with an error'}[operation]
        else:
            self.status = 'Ready to play' if self.verified else 'Game closed'
        return operation, code
