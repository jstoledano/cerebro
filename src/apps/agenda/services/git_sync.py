"""Registro y envio de un cambio de estado al repositorio Org."""
import subprocess


class GitSyncError(RuntimeError):
    pass


def git(repo, *args):
    command = ['git', '-C', str(repo), *args]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45, check=False)
    if result.returncode:
        raise GitSyncError((result.stderr or result.stdout or 'Error de Git').strip()[:600])
    return result.stdout.strip()


def assert_clean(repo):
    if git(repo, 'status', '--porcelain'):
        raise GitSyncError('El repositorio Org contiene cambios sin registrar. Sincroniza primero.')


def commit_and_push(repo, relative, task_id, new_state):
    """Solo se incluye el Org modificado. Los commits automatizados no llevan firma."""
    git(repo, 'add', '--', relative)
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-m',
        f'agenda: {task_id} -> {new_state}', '--', relative)
    sha = git(repo, 'rev-parse', 'HEAD')
    branch = git(repo, 'branch', '--show-current')
    if not branch:
        raise GitSyncError('HEAD separado; el commit local ya fue registrado.')
    git(repo, 'push', 'origin', branch)
    return sha
