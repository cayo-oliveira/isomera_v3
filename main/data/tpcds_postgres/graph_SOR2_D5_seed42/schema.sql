DROP SCHEMA IF EXISTS "scenario_sor2_d5_seed42" CASCADE;

CREATE SCHEMA "scenario_sor2_d5_seed42";

SELECT setseed(0.237);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d1_sor_customer" (
    "customer_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "customer_name" text,
    "email" text,
    "status" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d1_sor_customer_demographics" (
    "customer_demographics_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "gender_code" text,
    "education_level" text,
    "marital_status" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d4_sor_date_dim" (
    "date_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "calendar_date" date,
    "calendar_month" integer,
    "calendar_year" integer
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d5_sor_income_band" (
    "income_band_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "band_label" text,
    "lower_bound" integer,
    "upper_bound" integer
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d3_sor_item" (
    "item_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "item_name" text,
    "category_name" text,
    "list_price" numeric(12,2)
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d2_sor_nation" (
    "nation_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "nation_name" text,
    "iso_code" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d3_sor_promotion" (
    "promotion_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "promotion_name" text,
    "discount_pct" numeric(5,2)
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d2_sor_store" (
    "store_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "store_name" text,
    "store_type" text,
    "region_code" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d4_sor_time_dim" (
    "time_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "hour_of_day" integer,
    "minute_of_hour" integer,
    "shift_name" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d5_sor_warehouse" (
    "warehouse_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "warehouse_name" text,
    "capacity_units" integer
);

INSERT INTO "scenario_sor2_d5_seed42"."d1_sor_customer" ("customer_id", "benchmark_entity_id", "customer_name", "email", "status")
SELECT g, g, 'customer_' || g, 'customer_' || g || '@isomera.local', CASE WHEN g % 5 = 0 THEN 'inactive' ELSE 'active' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d1_sor_customer_demographics" ("customer_demographics_id", "benchmark_entity_id", "gender_code", "education_level", "marital_status")
SELECT g, g, CASE WHEN g % 2 = 0 THEN 'F' ELSE 'M' END, CASE WHEN g % 3 = 0 THEN 'graduate' ELSE 'college' END, CASE WHEN g % 2 = 0 THEN 'single' ELSE 'married' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d4_sor_date_dim" ("date_id", "benchmark_entity_id", "calendar_date", "calendar_month", "calendar_year")
SELECT g, g, date '2024-01-01' + ((g - 1) % 100), ((g - 1) % 12) + 1, 2024
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d5_sor_income_band" ("income_band_id", "benchmark_entity_id", "band_label", "lower_bound", "upper_bound")
SELECT g, g, 'band_' || g, g * 1000, (g * 1000) + 999
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d3_sor_item" ("item_id", "benchmark_entity_id", "item_name", "category_name", "list_price")
SELECT g, g, 'item_' || g, 'category_' || ((g % 7) + 1), round((10 + random() * 490)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d2_sor_nation" ("nation_id", "benchmark_entity_id", "nation_name", "iso_code")
SELECT g, g, 'nation_' || g, 'N' || lpad(g::text, 3, '0')
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d3_sor_promotion" ("promotion_id", "benchmark_entity_id", "promotion_name", "discount_pct")
SELECT g, g, 'promotion_' || g, round((random() * 35)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d2_sor_store" ("store_id", "benchmark_entity_id", "store_name", "store_type", "region_code")
SELECT g, g, 'store_' || g, CASE WHEN g % 2 = 0 THEN 'mall' ELSE 'street' END, 'r' || ((g % 5) + 1)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d4_sor_time_dim" ("time_id", "benchmark_entity_id", "hour_of_day", "minute_of_hour", "shift_name")
SELECT g, g, ((g - 1) % 24), ((g - 1) % 60), CASE WHEN ((g - 1) % 24) < 8 THEN 'night' WHEN ((g - 1) % 24) < 16 THEN 'day' ELSE 'evening' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d5_sor_warehouse" ("warehouse_id", "benchmark_entity_id", "warehouse_name", "capacity_units")
SELECT g, g, 'warehouse_' || g, 500 + g
FROM generate_series(1, 100) AS g;

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d3_sot_catalog_sales" (
    "catalog_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "item_id" integer,
    "promotion_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("item_id") REFERENCES "scenario_sor2_d5_seed42"."d3_sor_item" ("item_id"),
    FOREIGN KEY ("promotion_id") REFERENCES "scenario_sor2_d5_seed42"."d3_sor_promotion" ("promotion_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d2_sot_customer_attr" (
    "customer_attr_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "nation_id" integer,
    "store_id" integer,
    "customer_segment" text,
    "lifetime_value" numeric(14,2),
    FOREIGN KEY ("nation_id") REFERENCES "scenario_sor2_d5_seed42"."d2_sor_nation" ("nation_id"),
    FOREIGN KEY ("store_id") REFERENCES "scenario_sor2_d5_seed42"."d2_sor_store" ("store_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d2_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "nation_id" integer,
    "store_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("nation_id") REFERENCES "scenario_sor2_d5_seed42"."d2_sor_nation" ("nation_id"),
    FOREIGN KEY ("store_id") REFERENCES "scenario_sor2_d5_seed42"."d2_sor_store" ("store_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d3_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "item_id" integer,
    "promotion_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("item_id") REFERENCES "scenario_sor2_d5_seed42"."d3_sor_item" ("item_id"),
    FOREIGN KEY ("promotion_id") REFERENCES "scenario_sor2_d5_seed42"."d3_sor_promotion" ("promotion_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d4_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "date_id" integer,
    "time_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("date_id") REFERENCES "scenario_sor2_d5_seed42"."d4_sor_date_dim" ("date_id"),
    FOREIGN KEY ("time_id") REFERENCES "scenario_sor2_d5_seed42"."d4_sor_time_dim" ("time_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d5_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "income_band_id" integer,
    "warehouse_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("income_band_id") REFERENCES "scenario_sor2_d5_seed42"."d5_sor_income_band" ("income_band_id"),
    FOREIGN KEY ("warehouse_id") REFERENCES "scenario_sor2_d5_seed42"."d5_sor_warehouse" ("warehouse_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d5_sot_store_sales" (
    "store_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "income_band_id" integer,
    "warehouse_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("income_band_id") REFERENCES "scenario_sor2_d5_seed42"."d5_sor_income_band" ("income_band_id"),
    FOREIGN KEY ("warehouse_id") REFERENCES "scenario_sor2_d5_seed42"."d5_sor_warehouse" ("warehouse_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d1_sot_time_sales" (
    "time_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "customer_demographics_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor2_d5_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("customer_demographics_id") REFERENCES "scenario_sor2_d5_seed42"."d1_sor_customer_demographics" ("customer_demographics_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d1_sot_warehouse_stock" (
    "warehouse_stock_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "customer_demographics_id" integer,
    "on_hand_qty" integer,
    "reserved_qty" integer,
    "available_qty" integer,
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor2_d5_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("customer_demographics_id") REFERENCES "scenario_sor2_d5_seed42"."d1_sor_customer_demographics" ("customer_demographics_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d4_sot_warehouse_stock" (
    "warehouse_stock_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "date_id" integer,
    "time_id" integer,
    "on_hand_qty" integer,
    "reserved_qty" integer,
    "available_qty" integer,
    FOREIGN KEY ("date_id") REFERENCES "scenario_sor2_d5_seed42"."d4_sor_date_dim" ("date_id"),
    FOREIGN KEY ("time_id") REFERENCES "scenario_sor2_d5_seed42"."d4_sor_time_dim" ("time_id")
);

INSERT INTO "scenario_sor2_d5_seed42"."d3_sot_catalog_sales" ("catalog_sales_id", "benchmark_entity_id", "snapshot_date_id", "item_id", "promotion_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 6), round((40 + random() * 1100)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d2_sot_customer_attr" ("customer_attr_id", "benchmark_entity_id", "snapshot_date_id", "nation_id", "store_id", "customer_segment", "lifetime_value")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, CASE WHEN g % 3 = 0 THEN 'gold' WHEN g % 3 = 1 THEN 'silver' ELSE 'bronze' END, round((100 + random() * 5000)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d2_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "nation_id", "store_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d3_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "item_id", "promotion_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d4_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "date_id", "time_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d5_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "income_band_id", "warehouse_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d5_sot_store_sales" ("store_sales_id", "benchmark_entity_id", "snapshot_date_id", "income_band_id", "warehouse_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 9), round((30 + random() * 1200)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d1_sot_time_sales" ("time_sales_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "customer_demographics_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 5), round((20 + random() * 800)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d1_sot_warehouse_stock" ("warehouse_stock_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "customer_demographics_id", "on_hand_qty", "reserved_qty", "available_qty")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 50 + (g % 200), g % 20, (50 + (g % 200)) - (g % 20)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor2_d5_seed42"."d4_sot_warehouse_stock" ("warehouse_stock_id", "benchmark_entity_id", "snapshot_date_id", "date_id", "time_id", "on_hand_qty", "reserved_qty", "available_qty")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 50 + (g % 200), g % 20, (50 + (g % 200)) - (g % 20)
FROM generate_series(1, 100) AS g;

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d1_spec_catalog_performance" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor2_d5_seed42"."d1_sot_time_sales" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d1_spec_warehouse_logistics" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor2_d5_seed42"."d1_sot_warehouse_stock" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d4_spec_warehouse_logistics" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor2_d5_seed42"."d3_sot_customer_orders" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d3_spec_warehouse_logistics" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor2_d5_seed42"."d3_sot_catalog_sales" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d3_spec_time_analysis" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor2_d5_seed42"."d3_sot_catalog_sales" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d2_spec_time_analysis" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor2_d5_seed42"."d4_sot_warehouse_stock" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d2_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor2_d5_seed42"."d4_sot_customer_orders" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d4_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor2_d5_seed42"."d4_sot_customer_orders" p1
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

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d5_spec_store_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor2_d5_seed42"."d5_sot_customer_orders" p1
    JOIN "scenario_sor2_d5_seed42"."d5_sot_store_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor2_d5_seed42"."d5_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor2_d5_seed42"."d5_sot_customer_orders" p1
    JOIN "scenario_sor2_d5_seed42"."d5_spec_store_sales_summary" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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
