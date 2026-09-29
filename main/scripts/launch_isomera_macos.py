from __future__ import annotations

import json
import os
import re
import selectors
import shutil
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from isomera_identity import compact_identity_line, terminal_banner, terminal_status_banner


REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_ROOT = REPO_ROOT / "main"
LEGACY_VENV = REPO_ROOT / ".venv"
LOCAL_VENV_BASE = Path.home() / "Library" / "Application Support" / "Isomera" / "venvs"
DEFAULT_LOCAL_VENV = LOCAL_VENV_BASE / REPO_ROOT.name
VENV = Path(os.environ.get("ISOMERA_VENV_PATH", str(DEFAULT_LOCAL_VENV))).expanduser()
MANAGED_LOCAL_VENV = "ISOMERA_VENV_PATH" not in os.environ
try:
    LAUNCHER_VERSION = str(json.loads((MAIN_ROOT / "config" / "version.json").read_text(encoding="utf-8")).get("launcher_version", "unversioned"))
except (OSError, json.JSONDecodeError):
    LAUNCHER_VERSION = "unversioned"
MACOS_UF_DATALESS = 0x40000000
APP = MAIN_ROOT / "ui" / "app.py"
REQUIREMENTS = MAIN_ROOT / "requirements.txt"
LOG_DIR = MAIN_ROOT / "logs"
PORT = int(os.environ.get("ISOMERA_PORT", "8501"))
HOST = os.environ.get("ISOMERA_HOST", "localhost")
SHUTDOWN_REQUEST_PATH = Path(os.environ.get("ISOMERA_SHUTDOWN_REQUEST", str(LOG_DIR / "isomera_shutdown.request")))
MANAGE_LOCAL_DBS = os.environ.get("ISOMERA_MANAGE_LOCAL_DBS", "1") != "0"
POSTGRES_DATA_DIR = Path(os.environ.get("ISOMERA_POSTGRES_DATA_DIR", "/opt/homebrew/var/postgresql@16"))
POSTGRES_BIN_DIR = Path(os.environ.get("ISOMERA_POSTGRES_BIN_DIR", "/opt/homebrew/opt/postgresql@16/bin"))
MYSQL_SERVER = os.environ.get("ISOMERA_MYSQL_SERVER", shutil.which("mysql.server") or "/opt/homebrew/bin/mysql.server")
MYSQLADMIN = os.environ.get("ISOMERA_MYSQLADMIN", shutil.which("mysqladmin") or "/opt/homebrew/bin/mysqladmin")

KEY_DISTRIBUTIONS = [
    "streamlit",
    "sqlalchemy",
    "psycopg",
    "pymysql",
    "pandas",
    "networkx",
    "matplotlib",
    "plotly",
    "torch",
    "torch-geometric",
]


class LaunchError(RuntimeError):
    pass


class DatalessRuntimeError(LaunchError):
    pass


def _line() -> None:
    print("─" * 72, flush=True)


def _title() -> None:
    print("", flush=True)
    print(terminal_banner("BOOT"), flush=True)
    print(f"macOS local bootstrap · launcher v{LAUNCHER_VERSION}", flush=True)
    print(compact_identity_line(), flush=True)
    _line()


def _step(index: int, total: int, label: str) -> None:
    filled = int(index / total * 24)
    bar = "█" * filled + "░" * (24 - filled)
    print(f"[{bar}] {index}/{total}  {label}", flush=True)


def _run(command: list[str], *, timeout: int | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        env=env,
    )


def _run_probe(command: list[str], *, timeout: int = 12, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a short diagnostic without allowing a broken interpreter to freeze the launcher."""
    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        stdout, _ = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command, process.returncode, stdout or "")
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except Exception:
            pass
        return subprocess.CompletedProcess(
            command,
            124,
            f"Timeout após {timeout}s executando: {' '.join(command)}\n"
            "Isso normalmente indica Python/venv preso no macOS. Reinicie o macOS se o processo ficar em estado U/UE.",
        )


def _run_quiet(command: list[str], *, timeout: int = 20) -> subprocess.CompletedProcess[str] | None:
    try:
        return _run(command, timeout=timeout, env=_base_env())
    except Exception:
        return None


def _python() -> Path:
    return VENV / "bin" / "python"


def _streamlit() -> Path:
    return VENV / "bin" / "streamlit"


def _find_python311() -> str:
    for candidate in ("python3.11", "/opt/homebrew/bin/python3.11", "python3"):
        resolved = shutil.which(candidate) if not candidate.startswith("/") else candidate
        if not resolved or not Path(resolved).exists():
            continue
        result = _run([resolved, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"], timeout=10)
        if result.returncode == 0:
            major, minor = result.stdout.strip().split(".")[:2]
            if int(major) == 3 and int(minor) >= 11:
                return resolved
    raise LaunchError("Python 3.11+ não encontrado. Instale com `brew install python@3.11`.")


def _ensure_venv() -> None:
    dataless = _dataless_site_packages(VENV)
    if dataless:
        if not MANAGED_LOCAL_VENV:
            raise DatalessRuntimeError(
                f"A venv configurada explicitamente em {VENV} contém arquivos dataless. "
                "Não vou apagar um caminho personalizado automaticamente."
            )
        _remove_generated_venv(VENV, reason="a venv local gerenciada contém arquivos dataless")
    if VENV.exists() and not _python().exists():
        raise LaunchError(f"`{VENV}` existe, mas `{_python()}` não existe. Remova/recrie apenas essa venv local.")
    if not VENV.exists():
        py = _find_python311()
        VENV.parent.mkdir(parents=True, exist_ok=True)
        print(f"Criando ambiente Python local em {VENV} com {py}", flush=True)
        result = _run([py, "-m", "venv", str(VENV)], timeout=180)
        if result.returncode != 0:
            raise LaunchError(result.stdout)
    else:
        print(f"Reutilizando ambiente Python local existente: {VENV}", flush=True)


def _validate_venv() -> None:
    pyvenv_cfg = VENV / "pyvenv.cfg"
    if not pyvenv_cfg.exists():
        raise LaunchError(f"`{pyvenv_cfg}` nao encontrado em {VENV}. O ambiente local esta incompleto.")
    cfg = pyvenv_cfg.read_text(encoding="utf-8", errors="replace")
    version = ""
    for line in cfg.splitlines():
        if line.strip().startswith("version"):
            version = line.split("=", 1)[1].strip()
            break
    if not version:
        raise LaunchError(f"Nao consegui identificar a versao Python em {VENV}/pyvenv.cfg.")
    major, minor, *_ = version.split(".")
    if int(major) != 3 or int(minor) < 11:
        raise LaunchError(f"O ambiente Python em {VENV} usa Python {version}. Recomendado: Python 3.11+.")
    streamlit_script = _streamlit()
    if streamlit_script.exists():
        first_line = streamlit_script.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
        if ".venv-1" in first_line:
            raise LaunchError("O script Streamlit ainda aponta para `.venv-1`. Recrie o ambiente local gerenciado.")
    print(f"Python OK: {version} (validado por pyvenv.cfg, sem import pesado)", flush=True)


def _dataless_site_packages(venv_path: Path = VENV) -> list[tuple[Path, int]]:
    """Detect iCloud/File Provider placeholders before Python blocks importing them."""
    if sys.platform != "darwin":
        return []
    candidates = sorted((venv_path / "lib").glob("python*/site-packages"))
    if not candidates:
        return []
    found: list[tuple[Path, int]] = []
    for directory, _, filenames in os.walk(candidates[0]):
        for filename in filenames:
            path = Path(directory) / filename
            try:
                info = path.stat()
            except OSError:
                continue
            if info.st_flags & MACOS_UF_DATALESS:
                found.append((path, info.st_size))
    return found


def _dataless_message(files: list[tuple[Path, int]], venv_path: Path = VENV) -> str:
    total_mib = sum(size for _, size in files) / (1024 * 1024)
    examples = "\n".join(f"  - {path}" for path, _ in files[:8])
    if len(files) > 8:
        examples += f"\n  - ... e mais {len(files) - 8} arquivo(s)"
    return (
        f"{venv_path} contém {len(files)} arquivo(s) dataless ({total_mib:.1f} MiB).\n"
        f"Exemplos:\n{examples}\n"
        "O launcher não vai baixar esses arquivos da nuvem. A venv gerenciada será recriada em "
        f"{DEFAULT_LOCAL_VENV}, fora do iCloud."
    )


def _remove_generated_venv(path: Path, *, reason: str) -> None:
    resolved = path.resolve()
    is_legacy = path == LEGACY_VENV
    is_managed_local = MANAGED_LOCAL_VENV and resolved == DEFAULT_LOCAL_VENV.resolve()
    if path.is_symlink() or not (is_legacy or is_managed_local):
        raise LaunchError(f"Recusa em remover caminho de ambiente fora do escopo gerenciado: {path}")
    if not (path / "pyvenv.cfg").is_file():
        raise LaunchError(f"Recusa em remover {path}: não foi identificado como um ambiente virtual Python.")
    if is_legacy:
        ignored = _run(["git", "check-ignore", "-q", ".venv"], timeout=10)
        tracked = _run(["git", "ls-files", "--", ".venv"], timeout=10)
        if ignored.returncode != 0 or tracked.stdout.strip():
            raise LaunchError("A `.venv` antiga não está comprovadamente ignorada e sem arquivos rastreados; não será apagada.")
    print(f"Removendo ambiente virtual gerado em {path}: {reason}.", flush=True)
    shutil.rmtree(path)
    if path.exists():
        raise LaunchError(f"Não consegui remover completamente o ambiente virtual {path}.")


def _remove_legacy_dataless_venv() -> None:
    if not LEGACY_VENV.exists() or LEGACY_VENV.is_symlink():
        return
    if not (LEGACY_VENV / "pyvenv.cfg").is_file():
        return
    pending = _dataless_site_packages(LEGACY_VENV)
    if pending:
        print(
            f"A `.venv` antiga dentro de Documents tem {len(pending)} arquivos dataless; "
            "vou removê-la e usar um ambiente local fora do iCloud.",
            flush=True,
        )
        _remove_generated_venv(LEGACY_VENV, reason="migração para armazenamento local fora do iCloud")


def _site_packages() -> Path:
    candidates = sorted((VENV / "lib").glob("python*/site-packages"))
    if not candidates:
        raise LaunchError(f"site-packages nao encontrado dentro de {VENV}. Reinstale os requirements.")
    return candidates[0]


def _normalize_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _distribution_installed(distribution_name: str) -> bool:
    normalized = _normalize_distribution_name(distribution_name)
    site_packages = _site_packages()
    for path in site_packages.glob("*.dist-info"):
        installed = _normalize_distribution_name(path.name.split("-", 1)[0])
        if installed == normalized:
            return True
    return False


def _missing_distributions() -> list[str]:
    missing = []
    for dist in KEY_DISTRIBUTIONS:
        if not _distribution_installed(dist):
            missing.append(f"{dist}: not installed in local environment site-packages")
    return missing


def _run_streaming(command: list[str], *, timeout: int, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Stream pip output and carriage-return progress into the terminal/log as it arrives."""
    started = time.monotonic()
    last_heartbeat = started
    last_progress_print = started
    phase = "Resolvendo dependências e aguardando resposta do índice de pacotes"
    recent_output: deque[str] = deque(maxlen=50)
    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        text=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        env=env,
    )
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    pending = bytearray()
    latest_progress = ""
    stream_open = True

    def emit(raw: bytes, *, progress: bool = False) -> None:
        nonlocal phase, latest_progress, last_progress_print
        message = raw.decode("utf-8", errors="replace").strip()
        if not message:
            return
        if progress:
            latest_progress = message
            now = time.monotonic()
            if now - last_progress_print < 0.75:
                return
            last_progress_print = now
            label = f"[pip download] {message}"
        else:
            recent_output.append(message)
            match = re.fullmatch(r"Progress\s+(\d+)\s+of\s+(\d+)", message, flags=re.IGNORECASE)
            if match:
                current, total = (int(value) for value in match.groups())
                percent = min(100, round(current * 100 / total)) if total else 0
                filled = round(percent / 100 * 24)
                bar = "█" * filled + "░" * (24 - filled)
                downloaded = current / (1024 * 1024)
                size = total / (1024 * 1024)
                latest_progress = f"[{bar}] {percent:3d}% ({downloaded:.1f}/{size:.1f} MiB)"
                phase = "Baixando dependências"
                print(f"[download] {latest_progress}", flush=True)
                return
            lower = message.lower()
            if "looking in indexes" in lower or "collecting " in lower:
                phase = "Buscando e resolvendo pacotes"
            elif "downloading " in lower or "downloaded " in lower:
                phase = "Baixando dependências"
            elif "installing collected packages" in lower or "installing " in lower:
                phase = "Instalando pacotes"
            elif "successfully installed" in lower:
                phase = "Pacotes instalados; validando o resultado"
            elif "requirement already satisfied" in lower or "using cached" in lower:
                phase = "Reutilizando dependências disponíveis/cache"
            label = f"[pip] {message}"
        print(label, flush=True)

    while stream_open or process.poll() is None:
        events = selector.select(timeout=0.25)
        for key, _ in events:
            try:
                chunk = os.read(key.fd, 8192)
            except OSError as exc:
                recent_output.append(f"Erro lendo saída do pip: {exc}")
                chunk = b""
            if not chunk:
                selector.unregister(key.fileobj)
                stream_open = False
                if pending:
                    emit(bytes(pending))
                    pending.clear()
                continue
            for byte in chunk:
                if byte in (10, 13):
                    emit(bytes(pending), progress=(byte == 13))
                    pending.clear()
                else:
                    pending.append(byte)

        now = time.monotonic()
        if now - last_heartbeat >= 5 and process.poll() is None:
            elapsed = int(now - started)
            minutes, seconds = divmod(elapsed, 60)
            detail = f"; {latest_progress}" if latest_progress else ""
            print(f"[instalação {minutes:02d}:{seconds:02d}] {phase}{detail}…", flush=True)
            last_heartbeat = now
        if now - started > timeout and process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            selector.close()
            process.stdout.close()
            detail = "\n".join(recent_output)
            return subprocess.CompletedProcess(command, 124, detail + f"\nInstalação excedeu o limite de {timeout}s.")

    selector.close()
    returncode = process.wait()
    process.stdout.close()
    return subprocess.CompletedProcess(command, returncode, "\n".join(recent_output))


def _install_requirements() -> None:
    print(f"Instalando/atualizando dependências no ambiente local {VENV}.", flush=True)
    print("O terminal exibirá a busca, o progresso de download e a instalação de cada pacote.", flush=True)
    env = _base_env()
    env["PIP_PROGRESS_BAR"] = "raw"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_NO_INPUT"] = "1"
    command = [str(_python()), "-m", "pip", "install", "--progress-bar", "raw", "--disable-pip-version-check", "--no-input", "-r", str(REQUIREMENTS)]
    result = _run_streaming(command, timeout=900, env=env)
    if result.returncode != 0:
        raise LaunchError("Falha ao instalar requirements:\n" + result.stdout[-4000:])
    print("Instalação de dependências concluída.", flush=True)


def _base_env() -> dict[str, str]:
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(VENV)
    env["PATH"] = f"{VENV / 'bin'}:{env.get('PATH', '')}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("MPLCONFIGDIR", str(MAIN_ROOT / "data" / ".mplconfig"))
    env.setdefault("PSYCOPG_IMPL", "binary")
    env.pop("PYTHONHOME", None)
    return env


def _process_lines() -> list[str] | None:
    try:
        result = _run(["ps", "-ax"], timeout=10)
    except PermissionError:
        print("Não foi possível executar `ps -ax`.", flush=True)
        return None
    if result.returncode != 0:
        return None
    return result.stdout.splitlines()


def _pid_from_ps_line(line: str) -> int | None:
    parts = line.strip().split(None, 1)
    if not parts:
        return None
    try:
        return int(parts[0])
    except ValueError:
        return None


def _stale_streamlit_processes() -> list[tuple[int, str]] | None:
    current = os.getpid()
    stale: list[tuple[int, str]] = []
    app_path = str(APP.resolve())
    lines = _process_lines()
    if lines is None:
        return None
    for line in lines:
        if "streamlit" not in line or app_path not in line:
            continue
        pid = _pid_from_ps_line(line)
        if pid and pid != current:
            stale.append((pid, line.strip()))
    return stale


def _cleanup_stale_streamlit() -> None:
    stale = _stale_streamlit_processes()
    if stale is None:
        raise LaunchError("Não foi possível inspecionar processos antigos; para evitar duplicidade, não vou iniciar outra instância.")
    if not stale:
        print("Nenhum Streamlit antigo encontrado.", flush=True)
        return
    print("Streamlit antigo encontrado. Tentando encerrar:", flush=True)
    for pid, line in stale:
        print(f"  PID {pid}: {line}", flush=True)
        subprocess.run(["kill", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    remaining = _stale_streamlit_processes()
    if remaining is None:
        raise LaunchError("Não foi possível verificar a limpeza do Streamlit antigo; não vou iniciar outra instância.")
    for pid, _ in remaining:
        subprocess.run(["kill", "-9", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    remaining = _stale_streamlit_processes()
    if remaining is None:
        raise LaunchError("Não foi possível confirmar que o Streamlit antigo encerrou.")
    if remaining:
        print("Atenção: ainda existem processos presos. Se o estado for U/UE, o macOS pode exigir reinicialização.", flush=True)
        for pid, line in remaining:
            print(f"  preso PID {pid}: {line}", flush=True)
        raise LaunchError("Um processo Streamlit desta cópia continua ativo; a nova instância não será iniciada.")
    else:
        print("Processos antigos encerrados.", flush=True)


def _pg_ctl() -> Path:
    return POSTGRES_BIN_DIR / "pg_ctl"


def _pg_isready() -> Path:
    return POSTGRES_BIN_DIR / "pg_isready"


def _postgres_running() -> bool:
    pg_isready = _pg_isready()
    if pg_isready.exists():
        result = _run_quiet([str(pg_isready), "-q", "-h", "localhost", "-p", "5432"], timeout=10)
        return bool(result and result.returncode == 0)
    result = _run_quiet(["ps", "-ax"], timeout=10)
    return bool(result and "postgres" in result.stdout if result else False)


def _mysql_running() -> bool:
    mysqladmin = Path(MYSQLADMIN)
    if mysqladmin.exists():
        result = _run_quiet([str(mysqladmin), "ping", "-h", "127.0.0.1", "--silent"], timeout=10)
        return bool(result and result.returncode == 0)
    result = _run_quiet(["ps", "-ax"], timeout=10)
    return bool(result and "mysqld" in result.stdout if result else False)


def _start_postgres() -> bool:
    if _postgres_running():
        print("PostgreSQL já estava rodando. O launcher não vai encerrá-lo automaticamente.", flush=True)
        return False
    pg_ctl = _pg_ctl()
    if not pg_ctl.exists() or not POSTGRES_DATA_DIR.exists():
        print("PostgreSQL local não encontrado. Scenario Warehouse pode ficar indisponível.", flush=True)
        print(f"Esperado: {pg_ctl} e {POSTGRES_DATA_DIR}", flush=True)
        return False
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "postgres_launch.log"
    print("Iniciando PostgreSQL local para Scenario Warehouse...", flush=True)
    result = _run([str(pg_ctl), "-D", str(POSTGRES_DATA_DIR), "-l", str(log_path), "start"], timeout=45, env=_base_env())
    if result.returncode != 0:
        print("Não consegui iniciar PostgreSQL automaticamente.", flush=True)
        print(result.stdout[-1200:], flush=True)
        return False
    for _ in range(20):
        if _postgres_running():
            print("PostgreSQL pronto.", flush=True)
            return True
        time.sleep(0.5)
    print(f"PostgreSQL iniciou, mas não respondeu no tempo esperado. Log: {log_path}", flush=True)
    return True


def _stop_postgres() -> None:
    pg_ctl = _pg_ctl()
    if not pg_ctl.exists() or not POSTGRES_DATA_DIR.exists():
        return
    print("Encerrando PostgreSQL iniciado pelo Isomera...", flush=True)
    result = _run_quiet([str(pg_ctl), "-D", str(POSTGRES_DATA_DIR), "stop", "-m", "fast"], timeout=45)
    if not result or result.returncode != 0:
        print("PostgreSQL não confirmou shutdown automático. Se necessário, pare manualmente depois.", flush=True)


def _start_mysql() -> bool:
    if _mysql_running():
        print("MySQL já estava rodando. O launcher não vai encerrá-lo automaticamente.", flush=True)
        return False
    mysql_server = Path(MYSQL_SERVER)
    if not mysql_server.exists():
        print("MySQL local não encontrado. Backend MySQL adicional pode ficar indisponível.", flush=True)
        print(f"Esperado: {mysql_server}", flush=True)
        return False
    print("Iniciando MySQL local para backend/publicação...", flush=True)
    result = _run([str(mysql_server), "start"], timeout=60, env=_base_env())
    if result.returncode != 0 and "already running" not in result.stdout.lower():
        print("Não consegui iniciar MySQL automaticamente.", flush=True)
        print(result.stdout[-1200:], flush=True)
        return False
    for _ in range(30):
        if _mysql_running():
            print("MySQL pronto.", flush=True)
            return True
        time.sleep(0.5)
    print("MySQL iniciou, mas não respondeu no tempo esperado.", flush=True)
    return True


def _stop_mysql() -> None:
    mysql_server = Path(MYSQL_SERVER)
    if not mysql_server.exists():
        return
    print("Encerrando MySQL iniciado pelo Isomera...", flush=True)
    result = _run_quiet([str(mysql_server), "stop"], timeout=60)
    if not result or result.returncode != 0:
        print("MySQL não confirmou shutdown automático. Se necessário, pare manualmente depois.", flush=True)


def _start_local_databases() -> tuple[bool, bool]:
    if not MANAGE_LOCAL_DBS:
        print("Gerenciamento automático de bancos desativado por ISOMERA_MANAGE_LOCAL_DBS=0.", flush=True)
        return False, False
    postgres_started = _start_postgres()
    mysql_started = _start_mysql()
    return postgres_started, mysql_started


def _stop_local_databases(postgres_started: bool, mysql_started: bool) -> None:
    if mysql_started:
        _stop_mysql()
    if postgres_started:
        _stop_postgres()


def _port_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", PORT)) == 0


def _select_available_port() -> None:
    """Use the requested port or the next free local port; never terminate another application."""
    global PORT
    requested = PORT
    if not 1 <= requested <= 65535:
        raise LaunchError(f"Porta inválida: {requested}. Use ISOMERA_PORT entre 1 e 65535.")
    for candidate in range(requested, min(requested + 20, 65536)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", candidate))
            except OSError:
                continue
        PORT = candidate
        if candidate != requested:
            print(f"Porta {requested} ocupada por outro processo; Isomera usará {candidate}.", flush=True)
        else:
            print(f"Porta {candidate} disponível.", flush=True)
        return
    raise LaunchError(f"Nenhuma porta local livre entre {requested} e {min(requested + 19, 65535)}; nenhum processo externo foi encerrado.")


def _wait_for_port(process: subprocess.Popen[bytes], log_path: Path, timeout: int = 90) -> bool:
    start = time.time()
    spinner = "|/-\\"
    while time.time() - start < timeout:
        if process.poll() is not None:
            return False
        if _port_open():
            return True
        elapsed = int(time.time() - start)
        print(f"\rInicializando Streamlit {spinner[elapsed % len(spinner)]} {elapsed:02d}s", end="", flush=True)
        time.sleep(1)
    print("", flush=True)
    print(f"Streamlit ainda não respondeu após {timeout}s. Log: {log_path}", flush=True)
    return False


def _read_shutdown_request() -> str:
    try:
        return SHUTDOWN_REQUEST_PATH.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _consume_shutdown_request() -> str:
    payload = _read_shutdown_request()
    try:
        handled_path = SHUTDOWN_REQUEST_PATH.with_suffix(".handled")
        handled_path.write_text(payload, encoding="utf-8")
        SHUTDOWN_REQUEST_PATH.unlink(missing_ok=True)
    except Exception:
        pass
    return payload


def _tee_streamlit_output(process: subprocess.Popen[str], log_handle) -> threading.Thread:
    def reader() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            log_handle.write(line)
            log_handle.flush()
            print(f"streamlit | {line}", end="", flush=True)

    thread = threading.Thread(target=reader, name="streamlit-log-reader", daemon=True)
    thread.start()
    return thread


def _launch_streamlit() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    SHUTDOWN_REQUEST_PATH.unlink(missing_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"streamlit_launch_{timestamp}.log"
    command = [
        str(_python()),
        "-m",
        "streamlit",
        "run",
        str(APP),
        "--server.port",
        str(PORT),
        "--server.address",
        "localhost",
    ]
    print("Comando:", " ".join(command), flush=True)
    print(f"Log: {log_path}", flush=True)
    log_handle = log_path.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        env=_base_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    _tee_streamlit_output(process, log_handle)
    ready = _wait_for_port(process, log_path)
    if ready:
        url = f"http://{HOST}:{PORT}"
        print("\n" + terminal_status_banner("READY", "ISOMERA PRONTO PARA USO · STREAMLIT ATIVO"), flush=True)
        print(f"\nIsomera disponível em {url}", flush=True)
        subprocess.run(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("O Terminal ficará aberto com logs em tempo real.", flush=True)
        print("Para fechar com segurança: volte para este Terminal e pressione Ctrl+C uma vez.", flush=True)
        try:
            last_heartbeat = time.time()
            while process.poll() is None:
                time.sleep(1)
                if SHUTDOWN_REQUEST_PATH.exists():
                    payload = _consume_shutdown_request()
                    print("\nShutdown solicitado pelo app.", flush=True)
                    if payload:
                        print(f"shutdown | {payload.strip()[:1000]}", flush=True)
                    print("Encerrando Streamlit com segurança...", flush=True)
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        print("Streamlit não encerrou no tempo esperado. Forçando kill.", flush=True)
                        process.kill()
                        process.wait(timeout=10)
                    break
                if time.time() - last_heartbeat >= 30:
                    print(f"status | Isomera rodando em {url}. Log: {log_path}", flush=True)
                    last_heartbeat = time.time()
        except KeyboardInterrupt:
            print("\nCtrl+C recebido. Encerrando Streamlit com segurança...", flush=True)
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                print("Streamlit não encerrou no tempo esperado. Forçando kill.", flush=True)
                process.kill()
                process.wait(timeout=10)
        finally:
            log_handle.close()
        return
    process.terminate()
    time.sleep(3)
    if process.poll() is None:
        process.kill()
    log_handle.close()
    tail = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-80:]
    raise LaunchError("Streamlit não abriu a porta. Últimas linhas do log:\n" + "\n".join(tail))


def _goodbye() -> None:
    _line()
    print(terminal_banner("CLOSED"), flush=True)
    print("Isomera encerrado. Streamlit e recursos gerenciados foram finalizados.", flush=True)


def main() -> int:
    _title()
    steps = [
        "Verificar raiz do projeto",
        "Remover .venv antiga dataless do repo, se existir",
        "Criar ou reutilizar Python local fora do iCloud",
        "Validar Python e Streamlit",
        "Verificar dependências",
        "Encerrar somente Streamlit desta cópia do Isomera",
        "Escolher uma porta livre sem fechar outros aplicativos",
        "Iniciar apenas os bancos locais ausentes e gerenciados",
        "Abrir Isomera e verificar a inicialização",
    ]
    postgres_started = False
    mysql_started = False
    try:
        _step(1, len(steps), steps[0])
        if not APP.exists():
            raise LaunchError(f"App não encontrado: {APP}")
        if "--check-only" in sys.argv or os.environ.get("ISOMERA_LAUNCH_CHECK_ONLY") == "1":
            _step(2, len(steps), "Verificar o ambiente local sem modificar arquivos")
            print(f"Ambiente gerenciado esperado: {VENV}", flush=True)
            if not VENV.exists():
                print("Ambiente local ainda não existe; o launcher normal o criará e instalará requirements.", flush=True)
                return 1
            dataless = _dataless_site_packages(VENV)
            if dataless:
                print(_dataless_message(dataless, VENV), flush=True)
                return 2
            _validate_venv()
            missing = _missing_distributions()
            if missing:
                print("Dependências ausentes:", *missing, sep="\n  - ", flush=True)
                return 1
            print("Check-only concluído; sem instalação, remoção, encerramento de processo, alteração de banco ou abertura do app.", flush=True)
            return 0
        _step(2, len(steps), steps[1])
        _remove_legacy_dataless_venv()
        _step(3, len(steps), steps[2])
        _ensure_venv()
        _step(4, len(steps), steps[3])
        _validate_venv()
        _step(5, len(steps), steps[4])
        missing = _missing_distributions()
        if missing:
            print("Dependências ausentes ou com erro:", flush=True)
            for item in missing:
                print(f"  - {item}", flush=True)
            _install_requirements()
            missing = _missing_distributions()
            if missing:
                raise LaunchError("Ainda há dependências com erro:\n" + "\n".join(missing))
        print("Observação: o launcher valida pacotes instalados por metadados, não por import pesado, para evitar atrasos de inicialização no macOS.", flush=True)
        print("Dependências OK.", flush=True)
        print("\n" + terminal_status_banner("PKG READY", "PACOTES INSTALADOS E PRONTOS PARA USO"), flush=True)
        _step(6, len(steps), steps[5])
        _cleanup_stale_streamlit()
        _step(7, len(steps), steps[6])
        _select_available_port()
        _step(8, len(steps), steps[7])
        postgres_started, mysql_started = _start_local_databases()
        _step(9, len(steps), steps[8])
        _launch_streamlit()
        return 0
    except KeyboardInterrupt:
        print("\nInicialização interrompida pelo usuário.", flush=True)
        return 130
    except DatalessRuntimeError as exc:
        _line()
        print("Inicialização pausada: não foi possível preparar um ambiente local íntegro.", flush=True)
        print(str(exc), flush=True)
        print("Nenhum ambiente personalizado será apagado automaticamente.", flush=True)
        return 2
    except Exception as exc:
        _line()
        print("Falha ao iniciar o Isomera.", flush=True)
        print(str(exc), flush=True)
        print("", flush=True)
        print("Próximos passos:", flush=True)
        print("1. Feche terminais antigos do VS Code.", flush=True)
        print("2. Rode: ps -ax | grep streamlit", flush=True)
        print("3. Se houver processos em estado U/UE que não morrem com kill -9, reinicie o macOS.", flush=True)
        print("4. Depois abra novamente launch_isomera.command.", flush=True)
        return 1
    finally:
        _stop_local_databases(postgres_started, mysql_started)
        if "--check-only" not in sys.argv and os.environ.get("ISOMERA_LAUNCH_CHECK_ONLY") != "1":
            _goodbye()


if __name__ == "__main__":
    raise SystemExit(main())
