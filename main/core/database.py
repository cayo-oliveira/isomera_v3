"""Database connection and lineage extraction utilities."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import networkx as nx
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url


def create_sqlite_engine(database_path: str) -> Engine:
    """Create a SQLAlchemy engine for a SQLite database."""
    if database_path != ":memory:":
        path = Path(database_path)
        if not path.exists():
            raise FileNotFoundError(f"SQLite database not found: {database_path}")
        database_url = f"sqlite:///{path.resolve()}"
    else:
        database_url = "sqlite:///:memory:"

    return create_engine(database_url)


def create_database_engine(database_url: str) -> Engine:
    """Create a generic SQLAlchemy engine from a database URL."""
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)


def test_database_connection(database_url: str) -> dict[str, object]:
    """Return basic connection metadata for a database URL."""
    engine = create_database_engine(database_url)
    with engine.connect() as conn:
        if engine.dialect.name == "sqlite":
            current_database = database_url
            current_user = "sqlite"
        else:
            current_database = conn.execute(text("SELECT current_database()")).scalar_one_or_none()
            current_user = conn.execute(text("SELECT current_user")).scalar_one_or_none()
    inspector = inspect(engine)
    return {
        "database_url": database_url,
        "database": current_database,
        "user": current_user,
        "dialect": engine.dialect.name,
        "schema_count": len(list_database_schemas(database_url)),
        "table_count": sum(len(list_schema_tables(database_url, schema)) for schema in list_database_schemas(database_url)),
        "default_schema": inspector.default_schema_name,
    }


def list_database_schemas(database_url: str, include_system: bool = False) -> list[str]:
    """List schemas available in the target database."""
    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    schemas = inspector.get_schema_names()
    if include_system:
        return sorted(schemas)
    return sorted(
        schema
        for schema in schemas
        if schema not in {"information_schema", "pg_catalog", "pg_toast"}
        and not schema.startswith("pg_temp")
    )


def list_available_databases(database_url: str) -> list[str]:
    """List logical databases available for the current server/engine."""
    engine = create_database_engine(database_url)
    if engine.dialect.name == "sqlite":
        return [str(engine.url.database or ":memory:")]
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT datname
                FROM pg_database
                WHERE datistemplate = false
                ORDER BY datname
                """
            )
        ).fetchall()
    return [str(row[0]) for row in rows]


def replace_database_in_url(database_url: str, database_name: str) -> str:
    """Return a database URL pointing to another logical database on the same server."""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        return database_url
    return str(url.set(database=database_name))


def list_schema_tables(database_url: str, schema: str) -> list[str]:
    """List tables for a schema."""
    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    return sorted(inspector.get_table_names(schema=schema))


def list_table_columns(database_url: str, schema: str, table: str) -> pd.DataFrame:
    """Return column metadata for a table."""
    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    columns = inspector.get_columns(table, schema=schema)
    return pd.DataFrame(
        [
            {
                "column": column["name"],
                "type": str(column["type"]),
                "nullable": column.get("nullable"),
                "default": column.get("default"),
            }
            for column in columns
        ]
    )


def count_table_rows(database_url: str, schema: str, table: str) -> int:
    """Count rows in a table."""
    engine = create_database_engine(database_url)
    query = text(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
    with engine.connect() as conn:
        return int(conn.execute(query).scalar_one())


def preview_table(database_url: str, schema: str, table: str, limit: int = 50) -> pd.DataFrame:
    """Preview rows from a table."""
    engine = create_database_engine(database_url)
    query = text(f'SELECT * FROM "{schema}"."{table}" LIMIT {int(limit)}')
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def sql_statement_is_read_only(sql: str) -> bool:
    """Allow SELECT-like statements by default."""
    statement = sql.strip().lower().lstrip("(")
    return statement.startswith(("select", "with", "show", "explain"))


def run_sql_statement(
    database_url: str,
    sql: str,
    *,
    allow_mutation: bool = False,
) -> dict[str, object]:
    """Execute a SQL statement and return a structured result."""
    if not sql.strip():
        raise ValueError("SQL statement is empty.")
    if not allow_mutation and not sql_statement_is_read_only(sql):
        raise ValueError("Mutating SQL is locked. Enable the mutation toggle to run DDL/DML statements.")

    engine = create_database_engine(database_url)
    with engine.begin() as conn:
        result = conn.exec_driver_sql(sql)
        if result.returns_rows:
            rows = result.fetchall()
            columns = list(result.keys())
            dataframe = pd.DataFrame(rows, columns=columns)
            return {
                "type": "rows",
                "rowcount": len(dataframe),
                "dataframe": dataframe,
            }
        return {
            "type": "command",
            "rowcount": result.rowcount,
            "message": "Statement executed successfully.",
        }


def build_lineage_from_db(engine: Engine) -> nx.DiGraph:
    """Build a lineage graph using foreign key relationships in a database."""
    inspector = inspect(engine)
    graph = nx.DiGraph()

    table_names = inspector.get_table_names()
    for table in table_names:
        graph.add_node(table)

    for table in table_names:
        for foreign_key in inspector.get_foreign_keys(table):
            referred_table = foreign_key.get("referred_table")
            if referred_table:
                graph.add_edge(referred_table, table)

    return graph


def build_lineage_from_database_url(database_url: str, schema: str | None = None) -> nx.DiGraph:
    """Build a lineage graph from a database URL and optional schema."""
    engine = create_database_engine(database_url)
    inspector = inspect(engine)
    graph = nx.DiGraph()

    table_names = inspector.get_table_names(schema=schema)
    for table in table_names:
        graph.add_node(table)

    for table in table_names:
        for foreign_key in inspector.get_foreign_keys(table, schema=schema):
            referred_table = foreign_key.get("referred_table")
            if referred_table:
                graph.add_edge(referred_table, table)

    return graph


def ensure_scenario_validation_store(database_url: str) -> None:
    """Create the validation table used by curated scenario reviews."""
    engine = create_database_engine(database_url)
    ddl = """
    CREATE TABLE IF NOT EXISTS scenario_validation_pairs (
        scenario_name TEXT NOT NULL,
        node_a TEXT NOT NULL,
        node_b TEXT NOT NULL,
        decision TEXT NOT NULL,
        reviewed_at TEXT NOT NULL,
        source_gml_path TEXT,
        PRIMARY KEY (scenario_name, node_a, node_b)
    )
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))


def upsert_scenario_validation_pair(
    database_url: str,
    *,
    scenario_name: str,
    node_a: str,
    node_b: str,
    decision: str,
    reviewed_at: str,
    source_gml_path: str | None = None,
) -> None:
    """Upsert one curated validation decision into the scenario warehouse."""
    ensure_scenario_validation_store(database_url)
    engine = create_database_engine(database_url)
    delete_sql = text(
        """
        DELETE FROM scenario_validation_pairs
        WHERE scenario_name = :scenario_name AND node_a = :node_a AND node_b = :node_b
        """
    )
    insert_sql = text(
        """
        INSERT INTO scenario_validation_pairs (
            scenario_name, node_a, node_b, decision, reviewed_at, source_gml_path
        ) VALUES (
            :scenario_name, :node_a, :node_b, :decision, :reviewed_at, :source_gml_path
        )
        """
    )
    payload = {
        "scenario_name": scenario_name,
        "node_a": node_a,
        "node_b": node_b,
        "decision": decision,
        "reviewed_at": reviewed_at,
        "source_gml_path": source_gml_path,
    }
    with engine.begin() as conn:
        conn.execute(delete_sql, payload)
        conn.execute(insert_sql, payload)
