from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from isomera_identity import compact_identity_line, terminal_banner


REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_ROOT = REPO_ROOT / "main"
VENV = REPO_ROOT / ".venv"
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


def _line() -> None:
    print("─" * 72, flush=True)


def _title() -> None:
    print("", flush=True)
    print(terminal_banner("BOOT"), flush=True)
    print("macOS local bootstrap", flush=True)
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
    if VENV.exists() and not _python().exists():
        raise LaunchError(f"`{VENV}` existe, mas `{_python()}` não existe. Remova/recrie a venv.")
    if not VENV.exists():
        py = _find_python311()
        print(f"Criando .venv com {py}", flush=True)
        result = _run([py, "-m", "venv", str(VENV)], timeout=180)
        if result.returncode != 0:
            raise LaunchError(result.stdout)


def _validate_venv() -> None:
    pyvenv_cfg = VENV / "pyvenv.cfg"
    if not pyvenv_cfg.exists():
        raise LaunchError(f"`{pyvenv_cfg}` nao encontrado. Recrie a .venv.")
    cfg = pyvenv_cfg.read_text(encoding="utf-8", errors="replace")
    version = ""
    for line in cfg.splitlines():
        if line.strip().startswith("version"):
            version = line.split("=", 1)[1].strip()
            break
    if not version:
        raise LaunchError("Nao consegui identificar a versao Python em .venv/pyvenv.cfg.")
    major, minor, *_ = version.split(".")
    if int(major) != 3 or int(minor) < 11:
        raise LaunchError(f"A .venv atual usa Python {version}. Recomendado: Python 3.11+.")
    streamlit_script = _streamlit()
    if streamlit_script.exists():
        first_line = streamlit_script.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
        if ".venv-1" in first_line:
            raise LaunchError("O script `.venv/bin/streamlit` ainda aponta para `.venv-1`. Recrie a venv.")
    print(f"Python OK: {version} (validado por pyvenv.cfg, sem import pesado)", flush=True)


def _site_packages() -> Path:
    candidates = sorted((VENV / "lib").glob("python*/site-packages"))
    if not candidates:
        raise LaunchError("site-packages nao encontrado dentro da .venv. Reinstale os requirements.")
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
            missing.append(f"{dist}: not installed in .venv site-packages")
    return missing


def _install_requirements() -> None:
    print("Instalando/atualizando dependências da .venv. Isso pode demorar.", flush=True)
    result = _run([str(_python()), "-m", "pip", "install", "-r", str(REQUIREMENTS)], timeout=900, env=_base_env())
    if result.returncode != 0:
        raise LaunchError("Falha ao instalar requirements:\n" + result.stdout[-4000:])


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


def _process_lines() -> list[str]:
    try:
        result = _run(["ps", "-ax"], timeout=10)
    except PermissionError:
        print("Não foi possível executar `ps -ax` neste ambiente. Pulando limpeza automática de processos antigos.", flush=True)
        return []
    if result.returncode != 0:
        return []
    return result.stdout.splitlines()


def _pid_from_ps_line(line: str) -> int | None:
    parts = line.strip().split(None, 1)
    if not parts:
        return None
    try:
        return int(parts[0])
    except ValueError:
        return None


def _stale_streamlit_processes() -> list[tuple[int, str]]:
    current = os.getpid()
    stale: list[tuple[int, str]] = []
    for line in _process_lines():
        if "streamlit" not in line or "main/ui/app.py" not in line:
            continue
        pid = _pid_from_ps_line(line)
        if pid and pid != current:
            stale.append((pid, line.strip()))
    return stale


def _cleanup_stale_streamlit() -> None:
    stale = _stale_streamlit_processes()
    if not stale:
        print("Nenhum Streamlit antigo encontrado.", flush=True)
        return
    print("Streamlit antigo encontrado. Tentando encerrar:", flush=True)
    for pid, line in stale:
        print(f"  PID {pid}: {line}", flush=True)
        subprocess.run(["kill", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    remaining = _stale_streamlit_processes()
    for pid, _ in remaining:
        subprocess.run(["kill", "-9", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    remaining = _stale_streamlit_processes()
    if remaining:
        print("Atenção: ainda existem processos presos. Se o estado for U/UE, o macOS pode exigir reinicialização.", flush=True)
        for pid, line in remaining:
            print(f"  preso PID {pid}: {line}", flush=True)
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
        "Verificar/criar .venv correta",
        "Validar Python e Streamlit",
        "Verificar dependências",
        "Limpar Streamlit antigo",
        "Iniciar bancos locais",
        "Abrir Isomera",
    ]
    postgres_started = False
    mysql_started = False
    try:
        _step(1, len(steps), steps[0])
        if not APP.exists():
            raise LaunchError(f"App não encontrado: {APP}")
        _step(2, len(steps), steps[1])
        _ensure_venv()
        _step(3, len(steps), steps[2])
        _validate_venv()
        _step(4, len(steps), steps[3])
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
        _step(5, len(steps), steps[4])
        _cleanup_stale_streamlit()
        if "--check-only" in sys.argv or os.environ.get("ISOMERA_LAUNCH_CHECK_ONLY") == "1":
            print("Check-only concluído. O app não foi iniciado.", flush=True)
            return 0
        _step(6, len(steps), steps[5])
        postgres_started, mysql_started = _start_local_databases()
        _step(7, len(steps), steps[6])
        _launch_streamlit()
        return 0
    except KeyboardInterrupt:
        print("\nInicialização interrompida pelo usuário.", flush=True)
        return 130
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
