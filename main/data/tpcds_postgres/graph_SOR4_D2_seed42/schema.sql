DROP SCHEMA IF EXISTS "scenario_sor4_d2_seed42" CASCADE;

CREATE SCHEMA "scenario_sor4_d2_seed42";

SELECT setseed(0.218);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_sor_call_center" (
    "call_center_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "call_center_name" text,
    "service_tier" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_sor_customer" (
    "customer_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "customer_name" text,
    "email" text,
    "status" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_sor_customer_address" (
    "customer_address_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "street_name" text,
    "city_name" text,
    "state_code" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_sor_customer_demographics" (
    "customer_demographics_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "gender_code" text,
    "education_level" text,
    "marital_status" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_sor_loyalty_profile" (
    "loyalty_profile_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_sor_nation" (
    "nation_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "nation_name" text,
    "iso_code" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_sor_region" (
    "region_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "region_name" text,
    "geo_code" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_sor_store" (
    "store_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "store_name" text,
    "store_type" text,
    "region_code" text
);

INSERT INTO "scenario_sor4_d2_seed42"."d2_sor_call_center" ("call_center_id", "benchmark_entity_id", "call_center_name", "service_tier")
SELECT g, g, 'call_center_' || g, CASE WHEN g % 3 = 0 THEN 'gold' ELSE 'standard' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d1_sor_customer" ("customer_id", "benchmark_entity_id", "customer_name", "email", "status")
SELECT g, g, 'customer_' || g, 'customer_' || g || '@isomera.local', CASE WHEN g % 5 = 0 THEN 'inactive' ELSE 'active' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d1_sor_customer_address" ("customer_address_id", "benchmark_entity_id", "street_name", "city_name", "state_code")
SELECT g, g, 'street_' || g, 'city_' || ((g % 12) + 1), 'ST' || ((g % 9) + 1)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d1_sor_customer_demographics" ("customer_demographics_id", "benchmark_entity_id", "gender_code", "education_level", "marital_status")
SELECT g, g, CASE WHEN g % 2 = 0 THEN 'F' ELSE 'M' END, CASE WHEN g % 3 = 0 THEN 'graduate' ELSE 'college' END, CASE WHEN g % 2 = 0 THEN 'single' ELSE 'married' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d1_sor_loyalty_profile" ("loyalty_profile_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d2_sor_nation" ("nation_id", "benchmark_entity_id", "nation_name", "iso_code")
SELECT g, g, 'nation_' || g, 'N' || lpad(g::text, 3, '0')
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d2_sor_region" ("region_id", "benchmark_entity_id", "region_name", "geo_code")
SELECT g, g, 'region_' || g, 'geo_' || g
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d2_sor_store" ("store_id", "benchmark_entity_id", "store_name", "store_type", "region_code")
SELECT g, g, 'store_' || g, CASE WHEN g % 2 = 0 THEN 'mall' ELSE 'street' END, 'r' || ((g % 5) + 1)
FROM generate_series(1, 100) AS g;

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_sot_customer_attr" (
    "customer_attr_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "customer_address_id" integer,
    "customer_segment" text,
    "lifetime_value" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor4_d2_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("customer_address_id") REFERENCES "scenario_sor4_d2_seed42"."d1_sor_customer_address" ("customer_address_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_sot_customer_attr" (
    "customer_attr_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "region_id" integer,
    "store_id" integer,
    "customer_segment" text,
    "lifetime_value" numeric(14,2),
    FOREIGN KEY ("region_id") REFERENCES "scenario_sor4_d2_seed42"."d2_sor_region" ("region_id"),
    FOREIGN KEY ("store_id") REFERENCES "scenario_sor4_d2_seed42"."d2_sor_store" ("store_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "loyalty_profile_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor4_d2_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("loyalty_profile_id") REFERENCES "scenario_sor4_d2_seed42"."d1_sor_loyalty_profile" ("loyalty_profile_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "call_center_id" integer,
    "region_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("call_center_id") REFERENCES "scenario_sor4_d2_seed42"."d2_sor_call_center" ("call_center_id"),
    FOREIGN KEY ("region_id") REFERENCES "scenario_sor4_d2_seed42"."d2_sor_region" ("region_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_sot_warehouse_stock" (
    "warehouse_stock_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "loyalty_profile_id" integer,
    "on_hand_qty" integer,
    "reserved_qty" integer,
    "available_qty" integer,
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor4_d2_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("loyalty_profile_id") REFERENCES "scenario_sor4_d2_seed42"."d1_sor_loyalty_profile" ("loyalty_profile_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_sot_warehouse_stock" (
    "warehouse_stock_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "nation_id" integer,
    "region_id" integer,
    "on_hand_qty" integer,
    "reserved_qty" integer,
    "available_qty" integer,
    FOREIGN KEY ("nation_id") REFERENCES "scenario_sor4_d2_seed42"."d2_sor_nation" ("nation_id"),
    FOREIGN KEY ("region_id") REFERENCES "scenario_sor4_d2_seed42"."d2_sor_region" ("region_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_sot_web_sales" (
    "web_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "customer_address_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor4_d2_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("customer_address_id") REFERENCES "scenario_sor4_d2_seed42"."d1_sor_customer_address" ("customer_address_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_sot_web_sales" (
    "web_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "nation_id" integer,
    "store_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("nation_id") REFERENCES "scenario_sor4_d2_seed42"."d2_sor_nation" ("nation_id"),
    FOREIGN KEY ("store_id") REFERENCES "scenario_sor4_d2_seed42"."d2_sor_store" ("store_id")
);

INSERT INTO "scenario_sor4_d2_seed42"."d1_sot_customer_attr" ("customer_attr_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "customer_address_id", "customer_segment", "lifetime_value")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, CASE WHEN g % 3 = 0 THEN 'gold' WHEN g % 3 = 1 THEN 'silver' ELSE 'bronze' END, round((100 + random() * 5000)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d2_sot_customer_attr" ("customer_attr_id", "benchmark_entity_id", "snapshot_date_id", "region_id", "store_id", "customer_segment", "lifetime_value")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, CASE WHEN g % 3 = 0 THEN 'gold' WHEN g % 3 = 1 THEN 'silver' ELSE 'bronze' END, round((100 + random() * 5000)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d1_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "loyalty_profile_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d2_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "call_center_id", "region_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d1_sot_warehouse_stock" ("warehouse_stock_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "loyalty_profile_id", "on_hand_qty", "reserved_qty", "available_qty")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 50 + (g % 200), g % 20, (50 + (g % 200)) - (g % 20)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d2_sot_warehouse_stock" ("warehouse_stock_id", "benchmark_entity_id", "snapshot_date_id", "nation_id", "region_id", "on_hand_qty", "reserved_qty", "available_qty")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 50 + (g % 200), g % 20, (50 + (g % 200)) - (g % 20)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d1_sot_web_sales" ("web_sales_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "customer_address_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 7), round((25 + random() * 1400)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor4_d2_seed42"."d2_sot_web_sales" ("web_sales_id", "benchmark_entity_id", "snapshot_date_id", "nation_id", "store_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 7), round((25 + random() * 1400)::numeric, 2)
FROM generate_series(1, 100) AS g;

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_spec_catalog_performance" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d2_seed42"."d2_sot_customer_attr" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_spec_web_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d2_seed42"."d2_sot_customer_orders" p1
    JOIN "scenario_sor4_d2_seed42"."d2_sot_web_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
)
SELECT
    row_number() OVER () AS web_sales_summary_id,
    base.benchmark_entity_id,
    base.snapshot_date_id,
    round(sum(base.metric_value)::numeric, 2) AS total_web_sales,
    round(sum(base.metric_value)::numeric, 2) AS total_web_orders,
    round(avg(base.metric_value)::numeric, 2) AS avg_web_ticket
FROM base
GROUP BY base.benchmark_entity_id, base.snapshot_date_id
LIMIT 100;

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_spec_time_analysis" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d2_seed42"."d2_sot_web_sales" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_spec_warehouse_logistics" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d2_seed42"."d2_sot_warehouse_stock" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d1_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d2_seed42"."d1_sot_customer_attr" p1
    JOIN "scenario_sor4_d2_seed42"."d1_sot_customer_orders" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor4_d2_seed42"."d1_spec_catalog_performance" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d2_seed42"."d1_sot_customer_attr" p1
    JOIN "scenario_sor4_d2_seed42"."d1_sot_customer_orders" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor4_d2_seed42"."d1_spec_catalog_performance" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_spec_web_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d2_seed42"."d2_sot_customer_orders" p1
    JOIN "scenario_sor4_d2_seed42"."d2_sot_web_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor4_d2_seed42"."d2_spec_customer_summary" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
)
SELECT
    row_number() OVER () AS web_sales_summary_id,
    base.benchmark_entity_id,
    base.snapshot_date_id,
    round(sum(base.metric_value)::numeric, 2) AS total_web_sales,
    round(sum(base.metric_value)::numeric, 2) AS total_web_orders,
    round(avg(base.metric_value)::numeric, 2) AS avg_web_ticket
FROM base
GROUP BY base.benchmark_entity_id, base.snapshot_date_id
LIMIT 100;

CREATE TABLE IF NOT EXISTS "scenario_sor4_d2_seed42"."d2_spec_store_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor4_d2_seed42"."d2_sot_customer_orders" p1
    JOIN "scenario_sor4_d2_seed42"."d2_spec_customer_summary" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
)
SELECT
    row_number() OVER () AS store_sales_summary_id,
    base.benchmark_entity_id,
    base.snapshot_date_id,
    round(sum(base.metric_value)::numeric, 2) AS total_sales_amount,
    round(sum(base.metric_value)::numeric, 2) AS total_orders,
    round(sum(base.metric_value)::numeric, 2) AS distinct_customers
FROM base
GROUP BY base.benchmark_entity_id, base.snapshot_date_id
LIMIT 100;
