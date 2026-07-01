DROP SCHEMA IF EXISTS "scenario_sor4_d1_seed42" CASCADE;

CREATE SCHEMA "scenario_sor4_d1_seed42";

SELECT setseed(0.205);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_sor_customer" (
    "customer_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "customer_name" text,
    "email" text,
    "status" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_sor_customer_address" (
    "customer_address_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "street_name" text,
    "city_name" text,
    "state_code" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_sor_customer_demographics" (
    "customer_demographics_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "gender_code" text,
    "education_level" text,
    "marital_status" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_sor_loyalty_profile" (
    "loyalty_profile_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

INSERT INTO "scenario_sor4_d1_seed42"."d1_sor_customer" ("customer_id", "benchmark_entity_id", "customer_name", "email", "status")
SELECT g, g, 'customer_' || g, 'customer_' || g || '@isomera.local', CASE WHEN g % 5 = 0 THEN 'inactive' ELSE 'active' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d1_seed42"."d1_sor_customer_address" ("customer_address_id", "benchmark_entity_id", "street_name", "city_name", "state_code")
SELECT g, g, 'street_' || g, 'city_' || ((g % 12) + 1), 'ST' || ((g % 9) + 1)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d1_seed42"."d1_sor_customer_demographics" ("customer_demographics_id", "benchmark_entity_id", "gender_code", "education_level", "marital_status")
SELECT g, g, CASE WHEN g % 2 = 0 THEN 'F' ELSE 'M' END, CASE WHEN g % 3 = 0 THEN 'graduate' ELSE 'college' END, CASE WHEN g % 2 = 0 THEN 'single' ELSE 'married' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d1_seed42"."d1_sor_loyalty_profile" ("loyalty_profile_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_sot_customer_attr" (
    "customer_attr_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "customer_address_id" integer,
    "customer_segment" text,
    "lifetime_value" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor4_d1_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("customer_address_id") REFERENCES "scenario_sor4_d1_seed42"."d1_sor_customer_address" ("customer_address_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_sot_store_sales" (
    "store_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "customer_demographics_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor4_d1_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("customer_demographics_id") REFERENCES "scenario_sor4_d1_seed42"."d1_sor_customer_demographics" ("customer_demographics_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_sot_time_sales" (
    "time_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "customer_address_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor4_d1_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("customer_address_id") REFERENCES "scenario_sor4_d1_seed42"."d1_sor_customer_address" ("customer_address_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_sot_warehouse_stock" (
    "warehouse_stock_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_address_id" integer,
    "customer_demographics_id" integer,
    "on_hand_qty" integer,
    "reserved_qty" integer,
    "available_qty" integer,
    FOREIGN KEY ("customer_address_id") REFERENCES "scenario_sor4_d1_seed42"."d1_sor_customer_address" ("customer_address_id"),
    FOREIGN KEY ("customer_demographics_id") REFERENCES "scenario_sor4_d1_seed42"."d1_sor_customer_demographics" ("customer_demographics_id")
);

INSERT INTO "scenario_sor4_d1_seed42"."d1_sot_customer_attr" ("customer_attr_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "customer_address_id", "customer_segment", "lifetime_value")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, CASE WHEN g % 3 = 0 THEN 'gold' WHEN g % 3 = 1 THEN 'silver' ELSE 'bronze' END, round((100 + random() * 5000)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d1_seed42"."d1_sot_store_sales" ("store_sales_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "customer_demographics_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 9), round((30 + random() * 1200)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d1_seed42"."d1_sot_time_sales" ("time_sales_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "customer_address_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 5), round((20 + random() * 800)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d1_seed42"."d1_sot_warehouse_stock" ("warehouse_stock_id", "benchmark_entity_id", "snapshot_date_id", "customer_address_id", "customer_demographics_id", "on_hand_qty", "reserved_qty", "available_qty")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 50 + (g % 200), g % 20, (50 + (g % 200)) - (g % 20)
FROM generate_series(1, 100) AS g;

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_spec_time_analysis" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d1_seed42"."d1_sot_time_sales" p1
)
SELECT
    row_number() OVER () AS time_analysis_id,
    base.benchmark_entity_id,
    base.snapshot_date_id,
    round(sum(base.metric_value)::numeric, 2) AS total_sales_amount,
    round(sum(base.metric_value)::numeric, 2) AS peak_hour_sales,
    round(avg(base.metric_value)::numeric, 2) AS channel_mix_score
FROM base
GROUP BY base.benchmark_entity_id, base.snapshot_date_id
LIMIT 100;

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d1_seed42"."d1_sot_customer_attr" p1
)
SELECT
    row_number() OVER () AS customer_summary_id,
    base.benchmark_entity_id,
    base.snapshot_date_id,
    round(sum(base.metric_value)::numeric, 2) AS total_orders,
    round(sum(base.metric_value)::numeric, 2) AS total_revenue,
    round(avg(base.metric_value)::numeric, 2) AS avg_ticket
FROM base
GROUP BY base.benchmark_entity_id, base.snapshot_date_id
LIMIT 100;

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_spec_warehouse_logistics" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d1_seed42"."d1_sot_store_sales" p1
    JOIN "scenario_sor4_d1_seed42"."d1_sot_warehouse_stock" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
)
SELECT
    row_number() OVER () AS warehouse_logistics_id,
    base.benchmark_entity_id,
    base.snapshot_date_id,
    round(sum(base.metric_value)::numeric, 2) AS stock_turnover,
    round(sum(base.metric_value)::numeric, 2) AS days_of_supply,
    round(avg(base.metric_value)::numeric, 2) AS fill_rate
FROM base
GROUP BY base.benchmark_entity_id, base.snapshot_date_id
LIMIT 100;

CREATE TABLE IF NOT EXISTS "scenario_sor4_d1_seed42"."d1_spec_catalog_performance" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d1_seed42"."d1_sot_customer_attr" p1
    JOIN "scenario_sor4_d1_seed42"."d1_sot_store_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
)
SELECT
    row_number() OVER () AS catalog_performance_id,
    base.benchmark_entity_id,
    base.snapshot_date_id,
    round(sum(base.metric_value)::numeric, 2) AS catalog_sales_amount,
    round(sum(base.metric_value)::numeric, 2) AS store_sales_amount,
    round(avg(base.metric_value)::numeric, 2) AS conversion_rate
FROM base
GROUP BY base.benchmark_entity_id, base.snapshot_date_id
LIMIT 100;
