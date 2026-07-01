"""Relational persistence helpers for Isomera v2."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_ready(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload or {}


class Base(DeclarativeBase):
    """Base class for Isomera persistence models."""


class AppSession(Base):
    __tablename__ = "app_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    log_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    terminal_log_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ScenarioRecord(Base):
    __tablename__ = "scenarios"

    scenario_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    architecture_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    gml_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    labels_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    labels: Mapped[list["LabelVersionRecord"]] = relationship(back_populates="scenario")
    runs: Mapped[list["RunRecord"]] = relationship(back_populates="scenario")


class LabelVersionRecord(Base):
    __tablename__ = "label_versions"

    label_version: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.scenario_id"), nullable=False, index=True)
    label_count: Mapped[int] = mapped_column(Integer, nullable=False)
    label_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    scenario: Mapped["ScenarioRecord"] = relationship(back_populates="labels")


class ModelRecord(Base):
    __tablename__ = "models"

    model_version: Mapped[str] = mapped_column(String(255), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class RunRecord(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("app_sessions.id"), nullable=False, index=True)
    scenario_id: Mapped[Optional[str]] = mapped_column(ForeignKey("scenarios.scenario_id"), nullable=True, index=True)
    run_type: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    scenario: Mapped[Optional["ScenarioRecord"]] = relationship(back_populates="runs")
    reports: Mapped[list["ReportRecord"]] = relationship(back_populates="run")


class LogRecord(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("app_sessions.id"), nullable=False, index=True)
    run_id: Mapped[Optional[str]] = mapped_column(ForeignKey("runs.run_id"), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ReportRecord(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    run: Mapped["RunRecord"] = relationship(back_populates="reports")


class ArtifactRecord(Base):
    __tablename__ = "artifacts"

    artifact_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("app_sessions.id"), nullable=True, index=True)
    run_id: Mapped[Optional[str]] = mapped_column(ForeignKey("runs.run_id"), nullable=True, index=True)
    scenario_id: Mapped[Optional[str]] = mapped_column(ForeignKey("scenarios.scenario_id"), nullable=True, index=True)
    model_version: Mapped[Optional[str]] = mapped_column(ForeignKey("models.model_version"), nullable=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


@dataclass(frozen=True)
class BackendStatus:
    database_url: str
    scenario_count: int
    label_count: int
    run_count: int
    log_count: int
    report_count: int
    model_count: int
    artifact_count: int


def default_backend_database_url(project_root: str | Path) -> str:
    env_url = os.environ.get("ISOMERA_BACKEND_URL")
    if env_url:
        return env_url
    db_path = Path(project_root) / "data" / "backend" / "isomera_backend.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.resolve()}"


@lru_cache(maxsize=8)
def get_backend_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)


@lru_cache(maxsize=8)
def _get_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=get_backend_engine(database_url), future=True, expire_on_commit=False)


def init_backend_database(database_url: str) -> Engine:
    engine = get_backend_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def _scenario_id(architecture_name: str, scenario_name: str) -> str:
    return f"{architecture_name}:{scenario_name}"


def create_app_session(
    database_url: str,
    *,
    log_path: str | None,
    terminal_log_path: str | None,
    metadata: dict[str, Any] | None = None,
) -> str:
    init_backend_database(database_url)
    session_id = str(uuid.uuid4())
    session = AppSession(
        id=session_id,
        log_path=log_path,
        terminal_log_path=terminal_log_path,
        metadata_json=_json_ready(metadata),
    )
    with _get_session_factory(database_url)() as db:
        db.add(session)
        db.commit()
    return session_id


def touch_app_session(
    database_url: str,
    session_id: str,
    *,
    log_path: str | None = None,
    terminal_log_path: str | None = None,
) -> None:
    with _get_session_factory(database_url)() as db:
        session = db.get(AppSession, session_id)
        if session is None:
            return
        session.last_seen_at = _utcnow()
        if log_path:
            session.log_path = log_path
        if terminal_log_path:
            session.terminal_log_path = terminal_log_path
        db.commit()


def upsert_scenario(
    database_url: str,
    *,
    architecture_name: str,
    scenario_name: str,
    source: str,
    gml_path: str | None = None,
    labels_path: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    scenario_id = _scenario_id(architecture_name, scenario_name)
    with _get_session_factory(database_url)() as db:
        scenario = db.get(ScenarioRecord, scenario_id)
        if scenario is None:
            scenario = ScenarioRecord(
                scenario_id=scenario_id,
                architecture_name=architecture_name,
                scenario_name=scenario_name,
                source=source,
            )
            db.add(scenario)
        scenario.gml_path = gml_path
        scenario.labels_path = labels_path
        scenario.source = source
        scenario.metadata_json = _json_ready(metadata)
        scenario.updated_at = _utcnow()
        db.commit()
    return scenario_id


def create_label_version(
    database_url: str,
    *,
    scenario_id: str,
    labels: list[tuple[str, str]],
    metadata: dict[str, Any] | None = None,
) -> str:
    label_version = str(uuid.uuid4())
    payload = _json_ready(metadata)
    payload["pairs"] = [[a, b] for a, b in labels]
    with _get_session_factory(database_url)() as db:
        db.add(
            LabelVersionRecord(
                label_version=label_version,
                scenario_id=scenario_id,
                label_count=len(labels),
                label_payload=payload,
            )
        )
        db.commit()
    return label_version


def register_model_artifact(
    database_url: str,
    *,
    model_name: str,
    artifact_path: str,
    metadata: dict[str, Any] | None = None,
    model_version: str | None = None,
) -> str:
    version = model_version or f"{model_name}:{Path(artifact_path).name}"
    with _get_session_factory(database_url)() as db:
        model = db.get(ModelRecord, version)
        if model is None:
            model = ModelRecord(
                model_version=version,
                model_name=model_name,
                artifact_path=artifact_path,
            )
            db.add(model)
        model.artifact_path = artifact_path
        model.metadata_json = _json_ready(metadata)
        model.updated_at = _utcnow()
        db.commit()
    return version


def create_run(
    database_url: str,
    *,
    session_id: str,
    run_type: str,
    algorithm: str | None = None,
    scenario_id: str | None = None,
    parameters: dict[str, Any] | None = None,
    status: str = "running",
) -> str:
    run_id = str(uuid.uuid4())
    with _get_session_factory(database_url)() as db:
        db.add(
            RunRecord(
                run_id=run_id,
                session_id=session_id,
                scenario_id=scenario_id,
                run_type=run_type,
                algorithm=algorithm,
                status=status,
                parameters_json=_json_ready(parameters),
            )
        )
        db.commit()
    return run_id


def finalize_run(
    database_url: str,
    *,
    run_id: str,
    status: str,
    summary: dict[str, Any] | None = None,
) -> None:
    with _get_session_factory(database_url)() as db:
        run = db.get(RunRecord, run_id)
        if run is None:
            return
        run.status = status
        run.summary_json = _json_ready(summary)
        run.completed_at = _utcnow()
        db.commit()


def record_log_event(
    database_url: str,
    *,
    session_id: str,
    event: str,
    payload: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> None:
    with _get_session_factory(database_url)() as db:
        db.add(
            LogRecord(
                session_id=session_id,
                run_id=run_id,
                event=event,
                payload_json=_json_ready(payload),
            )
        )
        db.commit()


def create_report(
    database_url: str,
    *,
    run_id: str,
    report_type: str,
    summary: dict[str, Any] | None = None,
) -> int:
    with _get_session_factory(database_url)() as db:
        report = ReportRecord(
            run_id=run_id,
            report_type=report_type,
            summary_json=_json_ready(summary),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return int(report.id)


def register_artifact(
    database_url: str,
    *,
    artifact_type: str,
    path: str,
    session_id: str | None = None,
    run_id: str | None = None,
    scenario_id: str | None = None,
    model_version: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    artifact_id = str(uuid.uuid4())
    with _get_session_factory(database_url)() as db:
        db.add(
            ArtifactRecord(
                artifact_id=artifact_id,
                session_id=session_id,
                run_id=run_id,
                scenario_id=scenario_id,
                model_version=model_version,
                artifact_type=artifact_type,
                path=path,
                metadata_json=_json_ready(metadata),
            )
        )
        db.commit()
    return artifact_id


def backend_status(database_url: str) -> BackendStatus:
    init_backend_database(database_url)
    with _get_session_factory(database_url)() as db:
        return BackendStatus(
            database_url=database_url,
            scenario_count=int(db.scalar(select(func.count()).select_from(ScenarioRecord)) or 0),
            label_count=int(db.scalar(select(func.count()).select_from(LabelVersionRecord)) or 0),
            run_count=int(db.scalar(select(func.count()).select_from(RunRecord)) or 0),
            log_count=int(db.scalar(select(func.count()).select_from(LogRecord)) or 0),
            report_count=int(db.scalar(select(func.count()).select_from(ReportRecord)) or 0),
            model_count=int(db.scalar(select(func.count()).select_from(ModelRecord)) or 0),
            artifact_count=int(db.scalar(select(func.count()).select_from(ArtifactRecord)) or 0),
        )


def list_recent_runs(database_url: str, *, limit: int = 10) -> list[dict[str, Any]]:
    init_backend_database(database_url)
    with _get_session_factory(database_url)() as db:
        rows = db.scalars(select(RunRecord).order_by(RunRecord.started_at.desc()).limit(limit)).all()
        return [
            {
                "run_id": row.run_id,
                "run_type": row.run_type,
                "algorithm": row.algorithm,
                "status": row.status,
                "scenario_id": row.scenario_id,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }
            for row in rows
        ]


def list_recent_logs(database_url: str, *, limit: int = 20) -> list[dict[str, Any]]:
    init_backend_database(database_url)
    with _get_session_factory(database_url)() as db:
        rows = db.scalars(select(LogRecord).order_by(LogRecord.created_at.desc()).limit(limit)).all()
        return [
            {
                "event": row.event,
                "run_id": row.run_id,
                "session_id": row.session_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "payload": row.payload_json,
            }
            for row in rows
        ]


def list_recent_reports(database_url: str, *, limit: int = 20) -> list[dict[str, Any]]:
    init_backend_database(database_url)
    with _get_session_factory(database_url)() as db:
        rows = db.scalars(select(ReportRecord).order_by(ReportRecord.created_at.desc()).limit(limit)).all()
        return [
            {
                "report_id": int(row.id),
                "run_id": row.run_id,
                "report_type": row.report_type,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "summary": row.summary_json,
            }
            for row in rows
        ]


def resolve_database_url(database_url: str | None, project_root: str | Path) -> str:
    if database_url:
        return database_url
    return default_backend_database_url(project_root)
