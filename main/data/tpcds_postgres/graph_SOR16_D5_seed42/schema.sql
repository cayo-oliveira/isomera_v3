DROP SCHEMA IF EXISTS "scenario_sor16_d5_seed42" CASCADE;

CREATE SCHEMA "scenario_sor16_d5_seed42";

SELECT setseed(-0.149);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_call_center" (
    "call_center_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "call_center_name" text,
    "service_tier" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_customer" (
    "customer_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "customer_name" text,
    "email" text,
    "status" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_customer_address" (
    "customer_address_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "street_name" text,
    "city_name" text,
    "state_code" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_customer_demographics" (
    "customer_demographics_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "gender_code" text,
    "education_level" text,
    "marital_status" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_date_dim" (
    "date_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "calendar_date" date,
    "calendar_month" integer,
    "calendar_year" integer
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_engagement_signal" (
    "engagement_signal_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_regional_office" (
    "regional_office_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_merchandising_theme" (
    "merchandising_theme_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_business_day_flag" (
    "business_day_flag_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_transport_plan" (
    "transport_plan_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_customer_tier" (
    "customer_tier_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_store_format" (
    "store_format_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_return_policy" (
    "return_policy_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_school_calendar" (
    "school_calendar_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_route_cluster" (
    "route_cluster_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_channel_preference" (
    "channel_preference_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_location_segment" (
    "location_segment_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_catalog_slot" (
    "catalog_slot_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_promo_window" (
    "promo_window_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_handling_unit" (
    "handling_unit_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_identity_resolution" (
    "identity_resolution_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_demand_signal" (
    "demand_signal_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_closing_period" (
    "closing_period_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_carrier_contract" (
    "carrier_contract_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_working_shift_map" (
    "working_shift_map_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_loyalty_profile" (
    "loyalty_profile_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_district" (
    "district_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_brand" (
    "brand_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_fiscal_calendar" (
    "fiscal_calendar_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_logistics_partner" (
    "logistics_partner_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_household_profile" (
    "household_profile_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_market" (
    "market_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_category" (
    "category_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_holiday_calendar" (
    "holiday_calendar_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_carrier_service" (
    "carrier_service_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_customer_touchpoint" (
    "customer_touchpoint_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_territory" (
    "territory_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_supplier" (
    "supplier_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_week_dim" (
    "week_dim_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_distribution_route" (
    "distribution_route_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_support_case" (
    "support_case_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_store_zone" (
    "store_zone_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_inventory_snapshot" (
    "inventory_snapshot_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_month_dim" (
    "month_dim_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_fulfillment_batch" (
    "fulfillment_batch_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_digital_identity" (
    "digital_identity_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_location_bridge" (
    "location_bridge_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_assortment" (
    "assortment_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_quarter_dim" (
    "quarter_dim_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_shipment_event" (
    "shipment_event_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_preference_cluster" (
    "preference_cluster_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_operating_unit" (
    "operating_unit_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_item_taxonomy" (
    "item_taxonomy_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_season_dim" (
    "season_dim_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_return_reason" (
    "return_reason_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_consent_registry" (
    "consent_registry_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_geo_cluster" (
    "geo_cluster_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_product_bundle" (
    "product_bundle_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_event_calendar" (
    "event_calendar_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_dock_slot" (
    "dock_slot_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_household_income_proxy" (
    "household_income_proxy_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_service_area" (
    "service_area_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_vendor_program" (
    "vendor_program_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_pay_cycle" (
    "pay_cycle_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_vehicle_type" (
    "vehicle_type_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sor_service_subscription" (
    "service_subscription_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_trade_area" (
    "trade_area_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_price_band" (
    "price_band_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_reporting_period" (
    "reporting_period_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_delivery_wave" (
    "delivery_wave_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "entity_name" text,
    "entity_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_income_band" (
    "income_band_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "band_label" text,
    "lower_bound" integer,
    "upper_bound" integer
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_item" (
    "item_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "item_name" text,
    "category_name" text,
    "list_price" numeric(12,2)
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_nation" (
    "nation_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "nation_name" text,
    "iso_code" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_promotion" (
    "promotion_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "promotion_name" text,
    "discount_pct" numeric(5,2)
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sor_reason" (
    "reason_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "reason_name" text,
    "reason_group" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_region" (
    "region_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "region_name" text,
    "geo_code" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_ship_mode" (
    "ship_mode_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "ship_mode_name" text,
    "service_level" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sor_store" (
    "store_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "store_name" text,
    "store_type" text,
    "region_code" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sor_time_dim" (
    "time_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "hour_of_day" integer,
    "minute_of_hour" integer,
    "shift_name" text
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sor_warehouse" (
    "warehouse_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "warehouse_name" text,
    "capacity_units" integer
);

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_call_center" ("call_center_id", "benchmark_entity_id", "call_center_name", "service_tier")
SELECT g, g, 'call_center_' || g, CASE WHEN g % 3 = 0 THEN 'gold' ELSE 'standard' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_customer" ("customer_id", "benchmark_entity_id", "customer_name", "email", "status")
SELECT g, g, 'customer_' || g, 'customer_' || g || '@isomera.local', CASE WHEN g % 5 = 0 THEN 'inactive' ELSE 'active' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_customer_address" ("customer_address_id", "benchmark_entity_id", "street_name", "city_name", "state_code")
SELECT g, g, 'street_' || g, 'city_' || ((g % 12) + 1), 'ST' || ((g % 9) + 1)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_customer_demographics" ("customer_demographics_id", "benchmark_entity_id", "gender_code", "education_level", "marital_status")
SELECT g, g, CASE WHEN g % 2 = 0 THEN 'F' ELSE 'M' END, CASE WHEN g % 3 = 0 THEN 'graduate' ELSE 'college' END, CASE WHEN g % 2 = 0 THEN 'single' ELSE 'married' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_date_dim" ("date_id", "benchmark_entity_id", "calendar_date", "calendar_month", "calendar_year")
SELECT g, g, date '2024-01-01' + ((g - 1) % 100), ((g - 1) % 12) + 1, 2024
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_engagement_signal" ("engagement_signal_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_regional_office" ("regional_office_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_merchandising_theme" ("merchandising_theme_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_business_day_flag" ("business_day_flag_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_transport_plan" ("transport_plan_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_customer_tier" ("customer_tier_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_store_format" ("store_format_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_return_policy" ("return_policy_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_school_calendar" ("school_calendar_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_route_cluster" ("route_cluster_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_channel_preference" ("channel_preference_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_location_segment" ("location_segment_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_catalog_slot" ("catalog_slot_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_promo_window" ("promo_window_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_handling_unit" ("handling_unit_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_identity_resolution" ("identity_resolution_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_demand_signal" ("demand_signal_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_closing_period" ("closing_period_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_carrier_contract" ("carrier_contract_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_working_shift_map" ("working_shift_map_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_loyalty_profile" ("loyalty_profile_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_district" ("district_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_brand" ("brand_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_fiscal_calendar" ("fiscal_calendar_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_logistics_partner" ("logistics_partner_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_household_profile" ("household_profile_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_market" ("market_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_category" ("category_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_holiday_calendar" ("holiday_calendar_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_carrier_service" ("carrier_service_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_customer_touchpoint" ("customer_touchpoint_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_territory" ("territory_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_supplier" ("supplier_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_week_dim" ("week_dim_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_distribution_route" ("distribution_route_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_support_case" ("support_case_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_store_zone" ("store_zone_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_inventory_snapshot" ("inventory_snapshot_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_month_dim" ("month_dim_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_fulfillment_batch" ("fulfillment_batch_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_digital_identity" ("digital_identity_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_location_bridge" ("location_bridge_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_assortment" ("assortment_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_quarter_dim" ("quarter_dim_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_shipment_event" ("shipment_event_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_preference_cluster" ("preference_cluster_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_operating_unit" ("operating_unit_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_item_taxonomy" ("item_taxonomy_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_season_dim" ("season_dim_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_return_reason" ("return_reason_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_consent_registry" ("consent_registry_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_geo_cluster" ("geo_cluster_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_product_bundle" ("product_bundle_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_event_calendar" ("event_calendar_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_dock_slot" ("dock_slot_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_household_income_proxy" ("household_income_proxy_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_service_area" ("service_area_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_vendor_program" ("vendor_program_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_pay_cycle" ("pay_cycle_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_vehicle_type" ("vehicle_type_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sor_service_subscription" ("service_subscription_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_trade_area" ("trade_area_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_price_band" ("price_band_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_reporting_period" ("reporting_period_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_delivery_wave" ("delivery_wave_id", "benchmark_entity_id", "entity_name", "entity_group")
SELECT g, g, 'entity_' || g, 'benchmark'
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_income_band" ("income_band_id", "benchmark_entity_id", "band_label", "lower_bound", "upper_bound")
SELECT g, g, 'band_' || g, g * 1000, (g * 1000) + 999
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_item" ("item_id", "benchmark_entity_id", "item_name", "category_name", "list_price")
SELECT g, g, 'item_' || g, 'category_' || ((g % 7) + 1), round((10 + random() * 490)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_nation" ("nation_id", "benchmark_entity_id", "nation_name", "iso_code")
SELECT g, g, 'nation_' || g, 'N' || lpad(g::text, 3, '0')
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_promotion" ("promotion_id", "benchmark_entity_id", "promotion_name", "discount_pct")
SELECT g, g, 'promotion_' || g, round((random() * 35)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sor_reason" ("reason_id", "benchmark_entity_id", "reason_name", "reason_group")
SELECT g, g, 'reason_' || g, CASE WHEN g % 2 = 0 THEN 'return' ELSE 'support' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_region" ("region_id", "benchmark_entity_id", "region_name", "geo_code")
SELECT g, g, 'region_' || g, 'geo_' || g
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_ship_mode" ("ship_mode_id", "benchmark_entity_id", "ship_mode_name", "service_level")
SELECT g, g, CASE WHEN g % 3 = 0 THEN 'air' WHEN g % 3 = 1 THEN 'ground' ELSE 'sea' END, CASE WHEN g % 2 = 0 THEN 'express' ELSE 'standard' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sor_store" ("store_id", "benchmark_entity_id", "store_name", "store_type", "region_code")
SELECT g, g, 'store_' || g, CASE WHEN g % 2 = 0 THEN 'mall' ELSE 'street' END, 'r' || ((g % 5) + 1)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sor_time_dim" ("time_id", "benchmark_entity_id", "hour_of_day", "minute_of_hour", "shift_name")
SELECT g, g, ((g - 1) % 24), ((g - 1) % 60), CASE WHEN ((g - 1) % 24) < 8 THEN 'night' WHEN ((g - 1) % 24) < 16 THEN 'day' ELSE 'evening' END
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sor_warehouse" ("warehouse_id", "benchmark_entity_id", "warehouse_name", "capacity_units")
SELECT g, g, 'warehouse_' || g, 500 + g
FROM generate_series(1, 100) AS g;

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sot_catalog_sales" (
    "catalog_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "loyalty_profile_id" integer,
    "support_case_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("loyalty_profile_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_loyalty_profile" ("loyalty_profile_id"),
    FOREIGN KEY ("support_case_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_support_case" ("support_case_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sot_catalog_sales" (
    "catalog_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "location_bridge_id" integer,
    "nation_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("location_bridge_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_location_bridge" ("location_bridge_id"),
    FOREIGN KEY ("nation_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_nation" ("nation_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sot_catalog_sales" (
    "catalog_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "item_id" integer,
    "promotion_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("item_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_item" ("item_id"),
    FOREIGN KEY ("promotion_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_promotion" ("promotion_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sot_catalog_sales" (
    "catalog_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "quarter_dim_id" integer,
    "reporting_period_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("quarter_dim_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_quarter_dim" ("quarter_dim_id"),
    FOREIGN KEY ("reporting_period_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_reporting_period" ("reporting_period_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sot_catalog_sales" (
    "catalog_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "transport_plan_id" integer,
    "ship_mode_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("transport_plan_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_transport_plan" ("transport_plan_id"),
    FOREIGN KEY ("ship_mode_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_ship_mode" ("ship_mode_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sot_customer_attr" (
    "customer_attr_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "customer_address_id" integer,
    "customer_segment" text,
    "lifetime_value" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("customer_address_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_customer_address" ("customer_address_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sot_customer_attr" (
    "customer_attr_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "territory_id" integer,
    "trade_area_id" integer,
    "customer_segment" text,
    "lifetime_value" numeric(14,2),
    FOREIGN KEY ("territory_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_territory" ("territory_id"),
    FOREIGN KEY ("trade_area_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_trade_area" ("trade_area_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sot_customer_attr" (
    "customer_attr_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "catalog_slot_id" integer,
    "item_taxonomy_id" integer,
    "customer_segment" text,
    "lifetime_value" numeric(14,2),
    FOREIGN KEY ("catalog_slot_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_catalog_slot" ("catalog_slot_id"),
    FOREIGN KEY ("item_taxonomy_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_item_taxonomy" ("item_taxonomy_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sot_customer_attr" (
    "customer_attr_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "school_calendar_id" integer,
    "week_dim_id" integer,
    "customer_segment" text,
    "lifetime_value" numeric(14,2),
    FOREIGN KEY ("school_calendar_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_school_calendar" ("school_calendar_id"),
    FOREIGN KEY ("week_dim_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_week_dim" ("week_dim_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sot_customer_attr" (
    "customer_attr_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "handling_unit_id" integer,
    "return_reason_id" integer,
    "customer_segment" text,
    "lifetime_value" numeric(14,2),
    FOREIGN KEY ("handling_unit_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_handling_unit" ("handling_unit_id"),
    FOREIGN KEY ("return_reason_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_return_reason" ("return_reason_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "preference_cluster_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("preference_cluster_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_preference_cluster" ("preference_cluster_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "trade_area_id" integer,
    "store_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("trade_area_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_trade_area" ("trade_area_id"),
    FOREIGN KEY ("store_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_store" ("store_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "return_policy_id" integer,
    "product_bundle_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("return_policy_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_return_policy" ("return_policy_id"),
    FOREIGN KEY ("product_bundle_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_product_bundle" ("product_bundle_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "business_day_flag_id" integer,
    "fiscal_calendar_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("business_day_flag_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_business_day_flag" ("business_day_flag_id"),
    FOREIGN KEY ("fiscal_calendar_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_fiscal_calendar" ("fiscal_calendar_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sot_customer_orders" (
    "customer_orders_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "shipment_event_id" integer,
    "vehicle_type_id" integer,
    "order_count" integer,
    "order_amount" numeric(14,2),
    FOREIGN KEY ("shipment_event_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_shipment_event" ("shipment_event_id"),
    FOREIGN KEY ("vehicle_type_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_vehicle_type" ("vehicle_type_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sot_store_sales" (
    "store_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "customer_tier_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("customer_tier_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_customer_tier" ("customer_tier_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sot_store_sales" (
    "store_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "region_id" integer,
    "store_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("region_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_region" ("region_id"),
    FOREIGN KEY ("store_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_store" ("store_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sot_store_sales" (
    "store_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "merchandising_theme_id" integer,
    "promotion_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("merchandising_theme_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_merchandising_theme" ("merchandising_theme_id"),
    FOREIGN KEY ("promotion_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_promotion" ("promotion_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sot_store_sales" (
    "store_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "business_day_flag_id" integer,
    "month_dim_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("business_day_flag_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_business_day_flag" ("business_day_flag_id"),
    FOREIGN KEY ("month_dim_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_month_dim" ("month_dim_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sot_store_sales" (
    "store_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "route_cluster_id" integer,
    "vehicle_type_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("route_cluster_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_route_cluster" ("route_cluster_id"),
    FOREIGN KEY ("vehicle_type_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_vehicle_type" ("vehicle_type_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sot_time_sales" (
    "time_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "loyalty_profile_id" integer,
    "household_income_proxy_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("loyalty_profile_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_loyalty_profile" ("loyalty_profile_id"),
    FOREIGN KEY ("household_income_proxy_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_household_income_proxy" ("household_income_proxy_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sot_time_sales" (
    "time_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "market_id" integer,
    "service_area_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("market_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_market" ("market_id"),
    FOREIGN KEY ("service_area_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_service_area" ("service_area_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sot_time_sales" (
    "time_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "product_bundle_id" integer,
    "price_band_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("product_bundle_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_product_bundle" ("product_bundle_id"),
    FOREIGN KEY ("price_band_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_price_band" ("price_band_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sot_time_sales" (
    "time_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "date_id" integer,
    "time_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("date_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_date_dim" ("date_id"),
    FOREIGN KEY ("time_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_time_dim" ("time_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sot_time_sales" (
    "time_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "handling_unit_id" integer,
    "fulfillment_batch_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("handling_unit_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_handling_unit" ("handling_unit_id"),
    FOREIGN KEY ("fulfillment_batch_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_fulfillment_batch" ("fulfillment_batch_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sot_warehouse_stock" (
    "warehouse_stock_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_demographics_id" integer,
    "consent_registry_id" integer,
    "on_hand_qty" integer,
    "reserved_qty" integer,
    "available_qty" integer,
    FOREIGN KEY ("customer_demographics_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_customer_demographics" ("customer_demographics_id"),
    FOREIGN KEY ("consent_registry_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_consent_registry" ("consent_registry_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sot_warehouse_stock" (
    "warehouse_stock_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "geo_cluster_id" integer,
    "region_id" integer,
    "on_hand_qty" integer,
    "reserved_qty" integer,
    "available_qty" integer,
    FOREIGN KEY ("geo_cluster_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_geo_cluster" ("geo_cluster_id"),
    FOREIGN KEY ("region_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_region" ("region_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sot_warehouse_stock" (
    "warehouse_stock_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "catalog_slot_id" integer,
    "brand_id" integer,
    "on_hand_qty" integer,
    "reserved_qty" integer,
    "available_qty" integer,
    FOREIGN KEY ("catalog_slot_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_catalog_slot" ("catalog_slot_id"),
    FOREIGN KEY ("brand_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_brand" ("brand_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sot_warehouse_stock" (
    "warehouse_stock_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "closing_period_id" integer,
    "reporting_period_id" integer,
    "on_hand_qty" integer,
    "reserved_qty" integer,
    "available_qty" integer,
    FOREIGN KEY ("closing_period_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_closing_period" ("closing_period_id"),
    FOREIGN KEY ("reporting_period_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_reporting_period" ("reporting_period_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sot_warehouse_stock" (
    "warehouse_stock_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "ship_mode_id" integer,
    "warehouse_id" integer,
    "on_hand_qty" integer,
    "reserved_qty" integer,
    "available_qty" integer,
    FOREIGN KEY ("ship_mode_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_ship_mode" ("ship_mode_id"),
    FOREIGN KEY ("warehouse_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_warehouse" ("warehouse_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_sot_web_sales" (
    "web_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "customer_id" integer,
    "customer_address_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("customer_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_customer" ("customer_id"),
    FOREIGN KEY ("customer_address_id") REFERENCES "scenario_sor16_d5_seed42"."d1_sor_customer_address" ("customer_address_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_sot_web_sales" (
    "web_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "regional_office_id" integer,
    "market_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("regional_office_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_regional_office" ("regional_office_id"),
    FOREIGN KEY ("market_id") REFERENCES "scenario_sor16_d5_seed42"."d2_sor_market" ("market_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_sot_web_sales" (
    "web_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "inventory_snapshot_id" integer,
    "price_band_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("inventory_snapshot_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_inventory_snapshot" ("inventory_snapshot_id"),
    FOREIGN KEY ("price_band_id") REFERENCES "scenario_sor16_d5_seed42"."d3_sor_price_band" ("price_band_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_sot_web_sales" (
    "web_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "business_day_flag_id" integer,
    "event_calendar_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("business_day_flag_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_business_day_flag" ("business_day_flag_id"),
    FOREIGN KEY ("event_calendar_id") REFERENCES "scenario_sor16_d5_seed42"."d4_sor_event_calendar" ("event_calendar_id")
);

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_sot_web_sales" (
    "web_sales_id" integer PRIMARY KEY,
    "benchmark_entity_id" integer,
    "snapshot_date_id" integer,
    "logistics_partner_id" integer,
    "ship_mode_id" integer,
    "sales_qty" integer,
    "sales_amount" numeric(14,2),
    FOREIGN KEY ("logistics_partner_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_logistics_partner" ("logistics_partner_id"),
    FOREIGN KEY ("ship_mode_id") REFERENCES "scenario_sor16_d5_seed42"."d5_sor_ship_mode" ("ship_mode_id")
);

INSERT INTO "scenario_sor16_d5_seed42"."d1_sot_catalog_sales" ("catalog_sales_id", "benchmark_entity_id", "snapshot_date_id", "loyalty_profile_id", "support_case_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 6), round((40 + random() * 1100)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sot_catalog_sales" ("catalog_sales_id", "benchmark_entity_id", "snapshot_date_id", "location_bridge_id", "nation_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 6), round((40 + random() * 1100)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sot_catalog_sales" ("catalog_sales_id", "benchmark_entity_id", "snapshot_date_id", "item_id", "promotion_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 6), round((40 + random() * 1100)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sot_catalog_sales" ("catalog_sales_id", "benchmark_entity_id", "snapshot_date_id", "quarter_dim_id", "reporting_period_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 6), round((40 + random() * 1100)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sot_catalog_sales" ("catalog_sales_id", "benchmark_entity_id", "snapshot_date_id", "transport_plan_id", "ship_mode_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 6), round((40 + random() * 1100)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sot_customer_attr" ("customer_attr_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "customer_address_id", "customer_segment", "lifetime_value")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, CASE WHEN g % 3 = 0 THEN 'gold' WHEN g % 3 = 1 THEN 'silver' ELSE 'bronze' END, round((100 + random() * 5000)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sot_customer_attr" ("customer_attr_id", "benchmark_entity_id", "snapshot_date_id", "territory_id", "trade_area_id", "customer_segment", "lifetime_value")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, CASE WHEN g % 3 = 0 THEN 'gold' WHEN g % 3 = 1 THEN 'silver' ELSE 'bronze' END, round((100 + random() * 5000)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sot_customer_attr" ("customer_attr_id", "benchmark_entity_id", "snapshot_date_id", "catalog_slot_id", "item_taxonomy_id", "customer_segment", "lifetime_value")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, CASE WHEN g % 3 = 0 THEN 'gold' WHEN g % 3 = 1 THEN 'silver' ELSE 'bronze' END, round((100 + random() * 5000)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sot_customer_attr" ("customer_attr_id", "benchmark_entity_id", "snapshot_date_id", "school_calendar_id", "week_dim_id", "customer_segment", "lifetime_value")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, CASE WHEN g % 3 = 0 THEN 'gold' WHEN g % 3 = 1 THEN 'silver' ELSE 'bronze' END, round((100 + random() * 5000)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sot_customer_attr" ("customer_attr_id", "benchmark_entity_id", "snapshot_date_id", "handling_unit_id", "return_reason_id", "customer_segment", "lifetime_value")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, CASE WHEN g % 3 = 0 THEN 'gold' WHEN g % 3 = 1 THEN 'silver' ELSE 'bronze' END, round((100 + random() * 5000)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "preference_cluster_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "trade_area_id", "store_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "return_policy_id", "product_bundle_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "business_day_flag_id", "fiscal_calendar_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sot_customer_orders" ("customer_orders_id", "benchmark_entity_id", "snapshot_date_id", "shipment_event_id", "vehicle_type_id", "order_count", "order_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 4), round((50 + random() * 950)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sot_store_sales" ("store_sales_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "customer_tier_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 9), round((30 + random() * 1200)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sot_store_sales" ("store_sales_id", "benchmark_entity_id", "snapshot_date_id", "region_id", "store_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 9), round((30 + random() * 1200)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sot_store_sales" ("store_sales_id", "benchmark_entity_id", "snapshot_date_id", "merchandising_theme_id", "promotion_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 9), round((30 + random() * 1200)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sot_store_sales" ("store_sales_id", "benchmark_entity_id", "snapshot_date_id", "business_day_flag_id", "month_dim_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 9), round((30 + random() * 1200)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sot_store_sales" ("store_sales_id", "benchmark_entity_id", "snapshot_date_id", "route_cluster_id", "vehicle_type_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 9), round((30 + random() * 1200)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sot_time_sales" ("time_sales_id", "benchmark_entity_id", "snapshot_date_id", "loyalty_profile_id", "household_income_proxy_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 5), round((20 + random() * 800)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sot_time_sales" ("time_sales_id", "benchmark_entity_id", "snapshot_date_id", "market_id", "service_area_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 5), round((20 + random() * 800)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sot_time_sales" ("time_sales_id", "benchmark_entity_id", "snapshot_date_id", "product_bundle_id", "price_band_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 5), round((20 + random() * 800)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sot_time_sales" ("time_sales_id", "benchmark_entity_id", "snapshot_date_id", "date_id", "time_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 5), round((20 + random() * 800)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sot_time_sales" ("time_sales_id", "benchmark_entity_id", "snapshot_date_id", "handling_unit_id", "fulfillment_batch_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 5), round((20 + random() * 800)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sot_warehouse_stock" ("warehouse_stock_id", "benchmark_entity_id", "snapshot_date_id", "customer_demographics_id", "consent_registry_id", "on_hand_qty", "reserved_qty", "available_qty")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 50 + (g % 200), g % 20, (50 + (g % 200)) - (g % 20)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sot_warehouse_stock" ("warehouse_stock_id", "benchmark_entity_id", "snapshot_date_id", "geo_cluster_id", "region_id", "on_hand_qty", "reserved_qty", "available_qty")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 50 + (g % 200), g % 20, (50 + (g % 200)) - (g % 20)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sot_warehouse_stock" ("warehouse_stock_id", "benchmark_entity_id", "snapshot_date_id", "catalog_slot_id", "brand_id", "on_hand_qty", "reserved_qty", "available_qty")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 50 + (g % 200), g % 20, (50 + (g % 200)) - (g % 20)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sot_warehouse_stock" ("warehouse_stock_id", "benchmark_entity_id", "snapshot_date_id", "closing_period_id", "reporting_period_id", "on_hand_qty", "reserved_qty", "available_qty")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 50 + (g % 200), g % 20, (50 + (g % 200)) - (g % 20)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sot_warehouse_stock" ("warehouse_stock_id", "benchmark_entity_id", "snapshot_date_id", "ship_mode_id", "warehouse_id", "on_hand_qty", "reserved_qty", "available_qty")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 50 + (g % 200), g % 20, (50 + (g % 200)) - (g % 20)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d1_sot_web_sales" ("web_sales_id", "benchmark_entity_id", "snapshot_date_id", "customer_id", "customer_address_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 7), round((25 + random() * 1400)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d2_sot_web_sales" ("web_sales_id", "benchmark_entity_id", "snapshot_date_id", "regional_office_id", "market_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 7), round((25 + random() * 1400)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d3_sot_web_sales" ("web_sales_id", "benchmark_entity_id", "snapshot_date_id", "inventory_snapshot_id", "price_band_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 7), round((25 + random() * 1400)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d4_sot_web_sales" ("web_sales_id", "benchmark_entity_id", "snapshot_date_id", "business_day_flag_id", "event_calendar_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 7), round((25 + random() * 1400)::numeric, 2)
FROM generate_series(1, 100) AS g;

INSERT INTO "scenario_sor16_d5_seed42"."d5_sot_web_sales" ("web_sales_id", "benchmark_entity_id", "snapshot_date_id", "logistics_partner_id", "ship_mode_id", "sales_qty", "sales_amount")
SELECT g, g, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, ((g - 1) % 100) + 1, 1 + (g % 7), round((25 + random() * 1400)::numeric, 2)
FROM generate_series(1, 100) AS g;

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_spec_web_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d1_sot_customer_orders" p1
    JOIN "scenario_sor16_d5_seed42"."d1_sot_web_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_spec_warehouse_logistics" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d1_sot_store_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d1_sot_warehouse_stock" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_spec_warehouse_logistics" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d2_sot_store_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d2_sot_warehouse_stock" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_spec_catalog_performance" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d2_sot_catalog_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d2_sot_customer_attr" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d2_sot_store_sales" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_spec_time_analysis" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_catalog_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_time_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d3_sot_web_sales" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_spec_time_analysis" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_catalog_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_time_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d3_sot_web_sales" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_spec_time_analysis" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_catalog_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_time_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d3_sot_web_sales" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_spec_store_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_customer_orders" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_store_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_spec_web_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_customer_orders" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_web_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_customer_attr" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_customer_orders" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_spec_catalog_performance" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_catalog_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_customer_attr" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d3_sot_store_sales" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_spec_catalog_performance" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_catalog_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_customer_attr" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d3_sot_store_sales" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_spec_time_analysis" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d4_sot_catalog_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d4_sot_time_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d4_sot_web_sales" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_spec_catalog_performance" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d4_sot_catalog_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d4_sot_customer_attr" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d4_sot_store_sales" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_spec_warehouse_logistics" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d4_sot_store_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d4_sot_warehouse_stock" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_spec_warehouse_logistics" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d5_sot_store_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d5_sot_warehouse_stock" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_spec_store_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d5_sot_customer_orders" p1
    JOIN "scenario_sor16_d5_seed42"."d5_sot_store_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_spec_time_analysis" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d5_sot_catalog_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d5_sot_time_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d5_sot_web_sales" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_spec_catalog_performance" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d5_sot_catalog_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d5_sot_customer_attr" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d5_sot_store_sales" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d2_sot_customer_attr" p1
    JOIN "scenario_sor16_d5_seed42"."d2_sot_customer_orders" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d2_spec_catalog_performance" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d2_spec_store_sales_summary" p4 ON p4.benchmark_entity_id = p1.benchmark_entity_id AND p4.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_spec_web_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_customer_orders" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_web_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d3_spec_customer_summary" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d4_sot_customer_attr" p1
    JOIN "scenario_sor16_d5_seed42"."d4_sot_customer_orders" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d4_spec_catalog_performance" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d1_sot_customer_attr" p1
    JOIN "scenario_sor16_d5_seed42"."d1_sot_customer_orders" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d1_spec_catalog_performance" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d4_spec_store_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d2_sot_customer_orders" p1
    JOIN "scenario_sor16_d5_seed42"."d2_sot_store_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d2_spec_customer_summary" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d1_spec_store_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d1_sot_customer_orders" p1
    JOIN "scenario_sor16_d5_seed42"."d1_sot_store_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d1_spec_customer_summary" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d2_spec_web_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d1_sot_customer_orders" p1
    JOIN "scenario_sor16_d5_seed42"."d1_sot_web_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d1_spec_customer_summary" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_spec_store_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d1_sot_customer_orders" p1
    JOIN "scenario_sor16_d5_seed42"."d1_sot_store_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d1_spec_customer_summary" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d3_spec_warehouse_logistics" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_store_sales" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_warehouse_stock" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d3_spec_store_sales_summary" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_spec_customer_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d3_sot_customer_attr" p1
    JOIN "scenario_sor16_d5_seed42"."d3_sot_customer_orders" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d3_spec_catalog_performance" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d3_spec_store_sales_summary" p4 ON p4.benchmark_entity_id = p1.benchmark_entity_id AND p4.snapshot_date_id = p1.snapshot_date_id
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

CREATE TABLE IF NOT EXISTS "scenario_sor16_d5_seed42"."d5_spec_web_sales_summary" AS
WITH base AS (
    SELECT p1.benchmark_entity_id, p1.snapshot_date_id, (1.0 + (p1.benchmark_entity_id % 10))::numeric AS metric_value
    FROM "scenario_sor16_d5_seed42"."d5_sot_customer_orders" p1
    JOIN "scenario_sor16_d5_seed42"."d5_sot_web_sales" p2 ON p2.benchmark_entity_id = p1.benchmark_entity_id AND p2.snapshot_date_id = p1.snapshot_date_id
    JOIN "scenario_sor16_d5_seed42"."d5_spec_customer_summary" p3 ON p3.benchmark_entity_id = p1.benchmark_entity_id AND p3.snapshot_date_id = p1.snapshot_date_id
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
