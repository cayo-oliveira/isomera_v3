from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import networkx as nx


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GML_ROOT = PROJECT_ROOT / "main" / "data" / "architectures" / "tpc_ds" / "gml"
OUTPUT_ROOT = PROJECT_ROOT / "main" / "data" / "tpcds_postgres"

ALL_SCENARIOS = [
    f"graph_SOR{sor_count}_D{domain_count}_seed42"
    for sor_count in (2, 4, 8, 16)
    for domain_count in (1, 2, 3, 4, 5)
]

DOMAIN_NAMES = {
    1: "customer",
    2: "location_store",
    3: "product_catalog",
    4: "date_time",
    5: "logistics_fulfillment",
}

EXTRA_NAMES = {
    1: [
        "loyalty_profile",
        "household_profile",
        "customer_touchpoint",
        "support_case",
        "digital_identity",
        "preference_cluster",
        "consent_registry",
        "household_income_proxy",
        "service_subscription",
        "engagement_signal",
        "customer_tier",
        "channel_preference",
        "identity_resolution",
        "campaign_membership",
    ],
    2: [
        "district",
        "market",
        "territory",
        "store_zone",
        "location_bridge",
        "operating_unit",
        "geo_cluster",
        "service_area",
        "trade_area",
        "regional_office",
        "store_format",
        "location_segment",
        "channel_region",
        "coverage_map",
    ],
    3: [
        "brand",
        "category",
        "supplier",
        "inventory_snapshot",
        "assortment",
        "item_taxonomy",
        "product_bundle",
        "vendor_program",
        "price_band",
        "merchandising_theme",
        "return_policy",
        "catalog_slot",
        "demand_signal",
        "quality_grade",
    ],
    4: [
        "fiscal_calendar",
        "holiday_calendar",
        "week_dim",
        "month_dim",
        "quarter_dim",
        "season_dim",
        "event_calendar",
        "pay_cycle",
        "reporting_period",
        "business_day_flag",
        "school_calendar",
        "promo_window",
        "closing_period",
        "working_shift_map",
    ],
    5: [
        "logistics_partner",
        "carrier_service",
        "distribution_route",
        "fulfillment_batch",
        "shipment_event",
        "return_reason",
        "dock_slot",
        "vehicle_type",
        "delivery_wave",
        "transport_plan",
        "route_cluster",
        "handling_unit",
        "carrier_contract",
        "supply_lane",
    ],
}


@dataclass(frozen=True)
class ColumnDef:
    name: str
    sql_type: str
    expr: str
    primary_key: bool = False


BASE_SOR_COLUMNS = {
    "customer": [
        ColumnDef("customer_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("customer_name", "text", "'customer_' || g"),
        ColumnDef("email", "text", "'customer_' || g || '@isomera.local'"),
        ColumnDef("status", "text", "CASE WHEN g % 5 = 0 THEN 'inactive' ELSE 'active' END"),
    ],
    "customer_address": [
        ColumnDef("customer_address_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("street_name", "text", "'street_' || g"),
        ColumnDef("city_name", "text", "'city_' || ((g % 12) + 1)"),
        ColumnDef("state_code", "text", "'ST' || ((g % 9) + 1)"),
    ],
    "customer_demographics": [
        ColumnDef("customer_demographics_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("gender_code", "text", "CASE WHEN g % 2 = 0 THEN 'F' ELSE 'M' END"),
        ColumnDef("education_level", "text", "CASE WHEN g % 3 = 0 THEN 'graduate' ELSE 'college' END"),
        ColumnDef("marital_status", "text", "CASE WHEN g % 2 = 0 THEN 'single' ELSE 'married' END"),
    ],
    "store": [
        ColumnDef("store_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("store_name", "text", "'store_' || g"),
        ColumnDef("store_type", "text", "CASE WHEN g % 2 = 0 THEN 'mall' ELSE 'street' END"),
        ColumnDef("region_code", "text", "'r' || ((g % 5) + 1)"),
    ],
    "region": [
        ColumnDef("region_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("region_name", "text", "'region_' || g"),
        ColumnDef("geo_code", "text", "'geo_' || g"),
    ],
    "nation": [
        ColumnDef("nation_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("nation_name", "text", "'nation_' || g"),
        ColumnDef("iso_code", "text", "'N' || lpad(g::text, 3, '0')"),
    ],
    "call_center": [
        ColumnDef("call_center_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("call_center_name", "text", "'call_center_' || g"),
        ColumnDef("service_tier", "text", "CASE WHEN g % 3 = 0 THEN 'gold' ELSE 'standard' END"),
    ],
    "item": [
        ColumnDef("item_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("item_name", "text", "'item_' || g"),
        ColumnDef("category_name", "text", "'category_' || ((g % 7) + 1)"),
        ColumnDef("list_price", "numeric(12,2)", "round((10 + random() * 490)::numeric, 2)"),
    ],
    "promotion": [
        ColumnDef("promotion_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("promotion_name", "text", "'promotion_' || g"),
        ColumnDef("discount_pct", "numeric(5,2)", "round((random() * 35)::numeric, 2)"),
    ],
    "reason": [
        ColumnDef("reason_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("reason_name", "text", "'reason_' || g"),
        ColumnDef("reason_group", "text", "CASE WHEN g % 2 = 0 THEN 'return' ELSE 'support' END"),
    ],
    "date_dim": [
        ColumnDef("date_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("calendar_date", "date", "date '2024-01-01' + ((g - 1) % 100)"),
        ColumnDef("calendar_month", "integer", "((g - 1) % 12) + 1"),
        ColumnDef("calendar_year", "integer", "2024"),
    ],
    "time_dim": [
        ColumnDef("time_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("hour_of_day", "integer", "((g - 1) % 24)"),
        ColumnDef("minute_of_hour", "integer", "((g - 1) % 60)"),
        ColumnDef("shift_name", "text", "CASE WHEN ((g - 1) % 24) < 8 THEN 'night' WHEN ((g - 1) % 24) < 16 THEN 'day' ELSE 'evening' END"),
    ],
    "warehouse": [
        ColumnDef("warehouse_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("warehouse_name", "text", "'warehouse_' || g"),
        ColumnDef("capacity_units", "integer", "500 + g"),
    ],
    "ship_mode": [
        ColumnDef("ship_mode_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("ship_mode_name", "text", "CASE WHEN g % 3 = 0 THEN 'air' WHEN g % 3 = 1 THEN 'ground' ELSE 'sea' END"),
        ColumnDef("service_level", "text", "CASE WHEN g % 2 = 0 THEN 'express' ELSE 'standard' END"),
    ],
    "income_band": [
        ColumnDef("income_band_id", "integer", "g", primary_key=True),
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("band_label", "text", "'band_' || g"),
        ColumnDef("lower_bound", "integer", "g * 1000"),
        ColumnDef("upper_bound", "integer", "(g * 1000) + 999"),
    ],
}


GENERIC_SOR_TEMPLATE = [
    ColumnDef("generic_id", "integer", "g", primary_key=True),
    ColumnDef("benchmark_entity_id", "integer", "g"),
    ColumnDef("entity_name", "text", "'entity_' || g"),
    ColumnDef("entity_group", "text", "'benchmark'"),
]


SOT_MEASURES = {
    "customer_attr": [
        ColumnDef("customer_segment", "text", "CASE WHEN g % 3 = 0 THEN 'gold' WHEN g % 3 = 1 THEN 'silver' ELSE 'bronze' END"),
        ColumnDef("lifetime_value", "numeric(14,2)", "round((100 + random() * 5000)::numeric, 2)"),
    ],
    "customer_orders": [
        ColumnDef("order_count", "integer", "1 + (g % 4)"),
        ColumnDef("order_amount", "numeric(14,2)", "round((50 + random() * 950)::numeric, 2)"),
    ],
    "store_sales": [
        ColumnDef("sales_qty", "integer", "1 + (g % 9)"),
        ColumnDef("sales_amount", "numeric(14,2)", "round((30 + random() * 1200)::numeric, 2)"),
    ],
    "web_sales": [
        ColumnDef("sales_qty", "integer", "1 + (g % 7)"),
        ColumnDef("sales_amount", "numeric(14,2)", "round((25 + random() * 1400)::numeric, 2)"),
    ],
    "catalog_sales": [
        ColumnDef("sales_qty", "integer", "1 + (g % 6)"),
        ColumnDef("sales_amount", "numeric(14,2)", "round((40 + random() * 1100)::numeric, 2)"),
    ],
    "time_sales": [
        ColumnDef("sales_qty", "integer", "1 + (g % 5)"),
        ColumnDef("sales_amount", "numeric(14,2)", "round((20 + random() * 800)::numeric, 2)"),
    ],
    "warehouse_stock": [
        ColumnDef("on_hand_qty", "integer", "50 + (g % 200)"),
        ColumnDef("reserved_qty", "integer", "g % 20"),
        ColumnDef("available_qty", "integer", "(50 + (g % 200)) - (g % 20)"),
    ],
}


SPEC_MEASURES = {
    "customer_summary": ["total_orders", "total_revenue", "avg_ticket"],
    "store_sales_summary": ["total_sales_amount", "total_orders", "distinct_customers"],
    "web_sales_summary": ["total_web_sales", "total_web_orders", "avg_web_ticket"],
    "catalog_performance": ["catalog_sales_amount", "store_sales_amount", "conversion_rate"],
    "time_analysis": ["total_sales_amount", "peak_hour_sales", "channel_mix_score"],
    "warehouse_logistics": ["stock_turnover", "days_of_supply", "fill_rate"],
}


def snake_name(label: str) -> str:
    return label.lower()


def parse_node(node_label: str) -> tuple[str, str, int]:
    match = re.match(r"^(SOR|SOT|SPEC)_(.+)_D(\d+)$", node_label)
    if not match:
        raise ValueError(f"Unsupported node label: {node_label}")
    return match.group(1), match.group(2), int(match.group(3))


def canonical_semantic_name(raw_name: str, domain_id: int) -> str:
    if raw_name.startswith("extra_"):
        index = int(raw_name.split("_")[1])
        return EXTRA_NAMES[domain_id][index - 1]
    return raw_name


def table_name(node_label: str) -> str:
    node_type, raw_name, domain_id = parse_node(node_label)
    semantic_name = canonical_semantic_name(raw_name, domain_id)
    return f"d{domain_id}_{node_type.lower()}_{semantic_name}"


def pk_name(node_label: str) -> str:
    node_type, raw_name, domain_id = parse_node(node_label)
    semantic_name = canonical_semantic_name(raw_name, domain_id)
    if node_type == "SOR" and semantic_name in BASE_SOR_COLUMNS:
        for col in BASE_SOR_COLUMNS[semantic_name]:
            if col.primary_key:
                return col.name
    return f"{semantic_name}_id"


def sor_columns(node_label: str) -> list[ColumnDef]:
    _, raw_name, domain_id = parse_node(node_label)
    semantic_name = canonical_semantic_name(raw_name, domain_id)
    columns = BASE_SOR_COLUMNS.get(semantic_name)
    if columns is None:
        pk = ColumnDef(f"{semantic_name}_id", "integer", "g", primary_key=True)
        columns = [pk, *GENERIC_SOR_TEMPLATE[1:]]
    return columns


def sot_columns(node_label: str, parents: list[str]) -> list[ColumnDef]:
    _, raw_name, _ = parse_node(node_label)
    semantic_name = canonical_semantic_name(raw_name, parse_node(node_label)[2])
    pk = ColumnDef(f"{semantic_name}_id", "integer", "g", primary_key=True)
    columns = [
        pk,
        ColumnDef("benchmark_entity_id", "integer", "g"),
        ColumnDef("snapshot_date_id", "integer", "((g - 1) % 100) + 1"),
    ]
    for parent in sorted(parents):
        parent_table_pk = pk_name(parent)
        columns.append(
            ColumnDef(
                parent_table_pk,
                "integer",
                f"((g - 1) % 100) + 1",
            )
        )
    columns.extend(SOT_MEASURES[semantic_name])
    return columns


def render_create_table(schema_name: str, node_label: str, columns: list[ColumnDef], foreign_keys: list[str]) -> str:
    lines = [f'CREATE TABLE IF NOT EXISTS "{schema_name}"."{table_name(node_label)}" (']
    col_lines = []
    for col in columns:
        suffix = " PRIMARY KEY" if col.primary_key else ""
        col_lines.append(f'    "{col.name}" {col.sql_type}{suffix}')
    col_lines.extend(foreign_keys)
    lines.append(",\n".join(col_lines))
    lines.append(");")
    return "\n".join(lines)


def render_insert_sor(schema_name: str, node_label: str, columns: list[ColumnDef], row_count: int) -> str:
    names = ", ".join(f'"{col.name}"' for col in columns)
    exprs = ", ".join(col.expr for col in columns)
    return (
        f'INSERT INTO "{schema_name}"."{table_name(node_label)}" ({names})\n'
        f"SELECT {exprs}\n"
        f"FROM generate_series(1, {row_count}) AS g;"
    )


def render_insert_sot(schema_name: str, node_label: str, columns: list[ColumnDef], row_count: int) -> str:
    names = ", ".join(f'"{col.name}"' for col in columns)
    exprs = ", ".join(col.expr for col in columns)
    return (
        f'INSERT INTO "{schema_name}"."{table_name(node_label)}" ({names})\n'
        f"SELECT {exprs}\n"
        f"FROM generate_series(1, {row_count}) AS g;"
    )


def render_create_spec_table(schema_name: str, node_label: str, parents: list[str], row_count: int) -> str:
    _, raw_name, domain_id = parse_node(node_label)
    semantic_name = canonical_semantic_name(raw_name, domain_id)
    spec_id = f"{semantic_name}_id"
    measures = SPEC_MEASURES[semantic_name]
    parent_tables = [table_name(parent) for parent in sorted(parents)]
    aliases = [f"p{i + 1}" for i in range(len(parent_tables))]
    joins = []
    select_parts = [
        f"row_number() OVER () AS {spec_id}",
        "base.benchmark_entity_id",
        "base.snapshot_date_id",
    ]
    for measure in measures:
        if "avg" in measure or "rate" in measure or "score" in measure:
            select_parts.append(f"round(avg(base.metric_value)::numeric, 2) AS {measure}")
        else:
            select_parts.append(f"round(sum(base.metric_value)::numeric, 2) AS {measure}")
    if not parent_tables:
        raise ValueError(f"No parents found for SPEC node {node_label}")
    first_alias = aliases[0]
    from_clause = f'"{schema_name}"."{parent_tables[0]}" {first_alias}'
    ctes = [
        "WITH base AS (",
        f"    SELECT {first_alias}.benchmark_entity_id, {first_alias}.snapshot_date_id, (1.0 + ({first_alias}.benchmark_entity_id % 10))::numeric AS metric_value",
        f"    FROM {from_clause}",
    ]
    for alias, parent_table in zip(aliases[1:], parent_tables[1:]):
        joins.append(
            f'    JOIN "{schema_name}"."{parent_table}" {alias} '
            f"ON {alias}.benchmark_entity_id = {first_alias}.benchmark_entity_id "
            f"AND {alias}.snapshot_date_id = {first_alias}.snapshot_date_id"
        )
    if joins:
        ctes.extend(joins)
    ctes.append(")")
    create = [
        f'CREATE TABLE IF NOT EXISTS "{schema_name}"."{table_name(node_label)}" AS',
        *ctes,
        "SELECT",
        "    " + ",\n    ".join(select_parts),
        "FROM base",
        "GROUP BY base.benchmark_entity_id, base.snapshot_date_id",
        f"LIMIT {row_count};",
    ]
    return "\n".join(create)


def render_fk_line(schema_name: str, parent: str) -> str:
    parent_pk = pk_name(parent)
    parent_table = table_name(parent)
    return (
        f'    FOREIGN KEY ("{parent_pk}") REFERENCES "{schema_name}"."{parent_table}" ("{parent_pk}")'
    )


def schema_name_for_scenario(scenario_name: str) -> str:
    match = re.match(r"graph_SOR(\d+)_D(\d+)_seed(\d+)", scenario_name)
    if not match:
        raise ValueError(f"Unsupported scenario name: {scenario_name}")
    sor_count, domain_count, seed = match.groups()
    return f"scenario_sor{sor_count}_d{domain_count}_seed{seed}"


def postgres_seed_for_scenario(scenario_name: str) -> float:
    raw_seed = sum((index + 1) * ord(char) for index, char in enumerate(scenario_name))
    return round(((raw_seed % 1800) / 1000.0) - 0.9, 3)


def scenario_manifest(graph: nx.DiGraph, scenario_name: str) -> dict:
    manifest = {
        "scenario": scenario_name,
        "schema": schema_name_for_scenario(scenario_name),
        "domains": {},
        "edges": [{"from": u, "to": v} for u, v in graph.edges()],
    }
    for node, data in sorted(graph.nodes(data=True)):
        node_type, raw_name, domain_id = parse_node(node)
        manifest["domains"].setdefault(str(domain_id), {"name": DOMAIN_NAMES[domain_id], "tables": []})
        manifest["domains"][str(domain_id)]["tables"].append(
            {
                "node": node,
                "type": node_type,
                "raw_name": raw_name,
                "semantic_name": canonical_semantic_name(raw_name, domain_id),
                "table_name": table_name(node),
            }
        )
    return manifest


def generate_scenario_sql(scenario_name: str, row_count: int) -> tuple[str, dict]:
    graph = nx.read_gml(GML_ROOT / f"{scenario_name}.gml")
    schema_name = schema_name_for_scenario(scenario_name)
    build_order = list(nx.topological_sort(graph.reverse()))
    statements = [
        f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;',
        f'CREATE SCHEMA "{schema_name}";',
        f"SELECT setseed({postgres_seed_for_scenario(scenario_name)});",
    ]
    sor_nodes = [node for node in build_order if graph.nodes[node].get("type") == "SOR"]
    sot_nodes = [node for node in build_order if graph.nodes[node].get("type") == "SOT"]
    spec_nodes = [node for node in build_order if graph.nodes[node].get("type") == "SPEC"]

    for node in sorted(sor_nodes):
        columns = sor_columns(node)
        statements.append(render_create_table(schema_name, node, columns, []))
    for node in sorted(sor_nodes):
        statements.append(render_insert_sor(schema_name, node, sor_columns(node), row_count))

    for node in sorted(sot_nodes):
        parents = list(graph.successors(node))
        columns = sot_columns(node, parents)
        foreign_keys = [render_fk_line(schema_name, parent) for parent in sorted(parents)]
        statements.append(render_create_table(schema_name, node, columns, foreign_keys))
    for node in sorted(sot_nodes):
        statements.append(render_insert_sot(schema_name, node, sot_columns(node, list(graph.successors(node))), row_count))

    for node in spec_nodes:
        parents = list(graph.successors(node))
        statements.append(render_create_spec_table(schema_name, node, parents, row_count))

    manifest = scenario_manifest(graph, scenario_name)
    return "\n\n".join(statements) + "\n", manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PostgreSQL benchmark scripts for Isomera TPC-DS scenarios.")
    parser.add_argument("--row-count", type=int, default=100)
    parser.add_argument(
        "--scenarios",
        nargs="*",
        default=ALL_SCENARIOS,
        help="Scenario names to generate. Defaults to the complete 4x5 TPC-DS benchmark grid.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=OUTPUT_ROOT,
        help="Directory where schema.sql and manifest.json files will be written.",
    )
    args = parser.parse_args()

    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    manifests = []
    for scenario_name in args.scenarios:
        sql_text, manifest = generate_scenario_sql(scenario_name, row_count=args.row_count)
        scenario_dir = output_root / scenario_name
        scenario_dir.mkdir(parents=True, exist_ok=True)
        (scenario_dir / "schema.sql").write_text(sql_text, encoding="utf-8")
        (scenario_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        manifests.append(manifest)
    (output_root / "manifest.index.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
