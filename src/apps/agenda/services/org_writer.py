"""Transiciones serializadas sobre los dos Org autorizados."""
from contextlib import contextmanager
import os
from pathlib import Path
import shlex
import subprocess
import threading

from django.conf import settings
from django.core.management import call_command

from apps.agenda.services.data import load_payload
from apps.agenda.services.git_sync import GitSyncError, assert_clean, commit_and_push, git

_MUTEX = threading.RLock()


class StateChangeError(RuntimeError):
    pass


@contextmanager
def _exclusive(repo):
    path = repo / '.agenda-state.lock'
    # Archivo fuera del repositorio para conservar git status limpio.
    import hashlib
    import tempfile
    fingerprint = hashlib.sha256(str(repo).encode()).hexdigest()[:20]
    path = Path(tempfile.gettempdir()) / f'agenda-state-{fingerprint}.lock'
    with _MUTEX, path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def change_task_state(task_id: str, target: str, note: str):
    target = str(target).strip().upper()
    note = str(note).strip()
    if target not in ('TODO', 'DONE') or not 3 <= len(note) <= 4000:
        raise StateChangeError('Selecciona TODO o DONE y escribe una nota de 3 a 4000 caracteres.')
    if not task_id or len(task_id) > 120 or '\x00' in task_id:
        raise StateChangeError('ID de tarea invalido.')
    repo = Path(settings.AGENDA_PATH).expanduser().resolve()
    allowed = getattr(settings, 'AGENDA_FILES', [])
    if isinstance(allowed, str):
        allowed = [s.strip() for s in allowed.split(',') if s.strip()]
    with _exclusive(repo):
        payload = load_payload()
        matches = [x for x in payload['items'] if x.get('kind') == 'task' and x.get('id') == task_id]
        if len(matches) != 1:
            raise StateChangeError('La tarea debe tener un ID unico en la exportacion.')
        item = matches[0]
        if item.get('state') not in ('TODO', 'DONE') or item['state'] == target:
            raise StateChangeError('Transicion de estado invalida o redundante.')
        source = item.get('source')
        if source not in allowed:
            raise StateChangeError('El archivo Org de origen no esta autorizado.')
        org_file = (repo / source).resolve()
        if not org_file.is_file() or not org_file.is_relative_to(repo):
            raise StateChangeError('Ruta Org no autorizada.')
        try:
            assert_clean(repo)
            # Verificar divergencia antes de editar; se rechaza cualquier desfase.
            branch = git(repo, 'branch', '--show-current')
            if not branch:
                raise StateChangeError('El repositorio Org tiene HEAD separado.')
            git(repo, 'fetch', 'origin', branch)
            if git(repo, 'rev-parse', 'HEAD') != git(repo, 'rev-parse', 'FETCH_HEAD'):
                raise StateChangeError('El repositorio Org difiere del remoto. Actualiza antes de cambiar el estado.')
            command = shlex.split(getattr(settings, 'AGENDA_EMACS_COMMAND', 'emacs'))
            if not command:
                raise StateChangeError('AGENDA_EMACS_COMMAND no configurado.')
            script = Path(__file__).resolve().parents[1] / 'org' / 'change-state.el'
            # Compatibilidad con el Emacs Linux nativo y el comando WSL de desarrollo.
            if os.name == 'nt' and Path(command[0]).name.lower() in ('wsl', 'wsl.exe'):
                def wslpath(path):
                    result = subprocess.run(command[:-1] + ['--exec', 'wslpath', '-a', str(path).replace('\\', '/')],
                                            capture_output=True, text=True, timeout=20)
                    if result.returncode:
                        raise StateChangeError(result.stderr.strip())
                    return result.stdout.strip()
                script_arg, file_arg = wslpath(script), wslpath(org_file)
            else:
                script_arg, file_arg = str(script), str(org_file)
            result = subprocess.run(command + ['--batch', '-Q', '--script', script_arg, '--',
                                               file_arg, task_id, target, note],
                                    capture_output=True, text=True, timeout=90)
            if result.returncode:
                raise StateChangeError((result.stderr or result.stdout or 'Error de Emacs').strip()[-900:])
            if not result.stdout.strip().endswith(f'{item["state"]} {target}'):
                raise StateChangeError('Emacs no confirmo la transicion.')
            # La escritura Org ya ocurrio. Un error posterior requiere publicar el estado local.
            sha = None
            try:
                sha = commit_and_push(repo, source, task_id, target)
            except (GitSyncError, OSError) as exc:
                try:
                    call_command('agenda_export', verbosity=0)
                except Exception:
                    pass
                raise StateChangeError('Cambio local aplicado; sincronizacion Git pendiente: ' + str(exc)) from exc
            call_command('agenda_export', verbosity=0)
            return {'id': task_id, 'previous': item['state'], 'state': target, 'commit': sha}
        except GitSyncError as exc:
            raise StateChangeError(str(exc)) from exc
