graph [
  directed 1
  node [
    id 0
    label "SOR_call_center_D2"
    table_name "d2_sor_call_center"
    type "SOR"
    semantic_name "call_center"
    raw_name "call_center"
    domain "location_store"
  ]
  node [
    id 1
    label "SOR_nation_D2"
    table_name "d2_sor_nation"
    type "SOR"
    semantic_name "nation"
    raw_name "nation"
    domain "location_store"
  ]
  node [
    id 2
    label "SOR_region_D2"
    table_name "d2_sor_region"
    type "SOR"
    semantic_name "region"
    raw_name "region"
    domain "location_store"
  ]
  node [
    id 3
    label "SOR_store_D2"
    table_name "d2_sor_store"
    type "SOR"
    semantic_name "store"
    raw_name "store"
    domain "location_store"
  ]
  node [
    id 4
    label "SOT_customer_attr_D2"
    table_name "d2_sot_customer_attr"
    type "SOT"
    semantic_name "customer_attr"
    raw_name "customer_attr"
    domain "location_store"
  ]
  node [
    id 5
    label "SOT_customer_orders_D2"
    table_name "d2_sot_customer_orders"
    type "SOT"
    semantic_name "customer_orders"
    raw_name "customer_orders"
    domain "location_store"
  ]
  node [
    id 6
    label "SOT_warehouse_stock_D2"
    table_name "d2_sot_warehouse_stock"
    type "SOT"
    semantic_name "warehouse_stock"
    raw_name "warehouse_stock"
    domain "location_store"
  ]
  node [
    id 7
    label "SOT_web_sales_D2"
    table_name "d2_sot_web_sales"
    type "SOT"
    semantic_name "web_sales"
    raw_name "web_sales"
    domain "location_store"
  ]
  node [
    id 8
    label "SPEC_catalog_performance_D2"
    table_name "d2_spec_catalog_performance"
    type "SPEC"
    semantic_name "catalog_performance"
    raw_name "catalog_performance"
    domain "location_store"
  ]
  node [
    id 9
    label "SPEC_customer_summary_D2"
    table_name "d2_spec_customer_summary"
    type "SPEC"
    semantic_name "customer_summary"
    raw_name "customer_summary"
    domain "location_store"
  ]
  node [
    id 10
    label "SPEC_store_sales_summary_D2"
    table_name "d2_spec_store_sales_summary"
    type "SPEC"
    semantic_name "store_sales_summary"
    raw_name "store_sales_summary"
    domain "location_store"
  ]
  node [
    id 11
    label "SPEC_warehouse_logistics_D2"
    table_name "d2_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
    domain "location_store"
  ]
  node [
    id 12
    label "SOR_customer_D1"
    table_name "d1_sor_customer"
    type "SOR"
    semantic_name "customer"
    raw_name "customer"
    domain "customer"
  ]
  node [
    id 13
    label "SOR_customer_address_D1"
    table_name "d1_sor_customer_address"
    type "SOR"
    semantic_name "customer_address"
    raw_name "customer_address"
    domain "customer"
  ]
  node [
    id 14
    label "SOR_customer_demographics_D1"
    table_name "d1_sor_customer_demographics"
    type "SOR"
    semantic_name "customer_demographics"
    raw_name "customer_demographics"
    domain "customer"
  ]
  node [
    id 15
    label "SOR_extra_1_D1"
    table_name "d1_sor_loyalty_profile"
    type "SOR"
    semantic_name "loyalty_profile"
    raw_name "extra_1"
    domain "customer"
  ]
  node [
    id 16
    label "SOT_customer_attr_D1"
    table_name "d1_sot_customer_attr"
    type "SOT"
    semantic_name "customer_attr"
    raw_name "customer_attr"
    domain "customer"
  ]
  node [
    id 17
    label "SOT_customer_orders_D1"
    table_name "d1_sot_customer_orders"
    type "SOT"
    semantic_name "customer_orders"
    raw_name "customer_orders"
    domain "customer"
  ]
  node [
    id 18
    label "SOT_warehouse_stock_D1"
    table_name "d1_sot_warehouse_stock"
    type "SOT"
    semantic_name "warehouse_stock"
    raw_name "warehouse_stock"
    domain "customer"
  ]
  node [
    id 19
    label "SOT_web_sales_D1"
    table_name "d1_sot_web_sales"
    type "SOT"
    semantic_name "web_sales"
    raw_name "web_sales"
    domain "customer"
  ]
  node [
    id 20
    label "SPEC_catalog_performance_D1"
    table_name "d1_spec_catalog_performance"
    type "SPEC"
    semantic_name "catalog_performance"
    raw_name "catalog_performance"
    domain "customer"
  ]
  node [
    id 21
    label "SPEC_customer_summary_D1"
    table_name "d1_spec_customer_summary"
    type "SPEC"
    semantic_name "customer_summary"
    raw_name "customer_summary"
    domain "customer"
  ]
  node [
    id 22
    label "SPEC_time_analysis_D1"
    table_name "d1_spec_time_analysis"
    type "SPEC"
    semantic_name "time_analysis"
    raw_name "time_analysis"
    domain "customer"
  ]
  node [
    id 23
    label "SPEC_web_sales_summary_D1"
    table_name "d1_spec_web_sales_summary"
    type "SPEC"
    semantic_name "web_sales_summary"
    raw_name "web_sales_summary"
    domain "customer"
  ]
  node [
    id 24
    label "SOR_date_dim_D4"
    table_name "d4_sor_date_dim"
    type "SOR"
    semantic_name "date_dim"
    raw_name "date_dim"
    domain "date_time"
  ]
  node [
    id 25
    label "SOR_extra_1_D4"
    table_name "d4_sor_fiscal_calendar"
    type "SOR"
    semantic_name "fiscal_calendar"
    raw_name "extra_1"
    domain "date_time"
  ]
  node [
    id 26
    label "SOR_extra_2_D4"
    table_name "d4_sor_holiday_calendar"
    type "SOR"
    semantic_name "holiday_calendar"
    raw_name "extra_2"
    domain "date_time"
  ]
  node [
    id 27
    label "SOR_time_dim_D4"
    table_name "d4_sor_time_dim"
    type "SOR"
    semantic_name "time_dim"
    raw_name "time_dim"
    domain "date_time"
  ]
  node [
    id 28
    label "SOT_store_sales_D4"
    table_name "d4_sot_store_sales"
    type "SOT"
    semantic_name "store_sales"
    raw_name "store_sales"
    domain "date_time"
  ]
  node [
    id 29
    label "SOT_time_sales_D4"
    table_name "d4_sot_time_sales"
    type "SOT"
    semantic_name "time_sales"
    raw_name "time_sales"
    domain "date_time"
  ]
  node [
    id 30
    label "SOT_warehouse_stock_D4"
    table_name "d4_sot_warehouse_stock"
    type "SOT"
    semantic_name "warehouse_stock"
    raw_name "warehouse_stock"
    domain "date_time"
  ]
  node [
    id 31
    label "SOT_web_sales_D4"
    table_name "d4_sot_web_sales"
    type "SOT"
    semantic_name "web_sales"
    raw_name "web_sales"
    domain "date_time"
  ]
  node [
    id 32
    label "SPEC_customer_summary_D4"
    table_name "d4_spec_customer_summary"
    type "SPEC"
    semantic_name "customer_summary"
    raw_name "customer_summary"
    domain "date_time"
  ]
  node [
    id 33
    label "SPEC_store_sales_summary_D4"
    table_name "d4_spec_store_sales_summary"
    type "SPEC"
    semantic_name "store_sales_summary"
    raw_name "store_sales_summary"
    domain "date_time"
  ]
  node [
    id 34
    label "SPEC_time_analysis_D4"
    table_name "d4_spec_time_analysis"
    type "SPEC"
    semantic_name "time_analysis"
    raw_name "time_analysis"
    domain "date_time"
  ]
  node [
    id 35
    label "SPEC_warehouse_logistics_D4"
    table_name "d4_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
    domain "date_time"
  ]
  node [
    id 36
    label "SOR_extra_1_D3"
    table_name "d3_sor_brand"
    type "SOR"
    semantic_name "brand"
    raw_name "extra_1"
    domain "product_catalog"
  ]
  node [
    id 37
    label "SOR_item_D3"
    table_name "d3_sor_item"
    type "SOR"
    semantic_name "item"
    raw_name "item"
    domain "product_catalog"
  ]
  node [
    id 38
    label "SOR_promotion_D3"
    table_name "d3_sor_promotion"
    type "SOR"
    semantic_name "promotion"
    raw_name "promotion"
    domain "product_catalog"
  ]
  node [
    id 39
    label "SOR_reason_D3"
    table_name "d3_sor_reason"
    type "SOR"
    semantic_name "reason"
    raw_name "reason"
    domain "product_catalog"
  ]
  node [
    id 40
    label "SOT_catalog_sales_D3"
    table_name "d3_sot_catalog_sales"
    type "SOT"
    semantic_name "catalog_sales"
    raw_name "catalog_sales"
    domain "product_catalog"
  ]
  node [
    id 41
    label "SOT_customer_orders_D3"
    table_name "d3_sot_customer_orders"
    type "SOT"
    semantic_name "customer_orders"
    raw_name "customer_orders"
    domain "product_catalog"
  ]
  node [
    id 42
    label "SOT_store_sales_D3"
    table_name "d3_sot_store_sales"
    type "SOT"
    semantic_name "store_sales"
    raw_name "store_sales"
    domain "product_catalog"
  ]
  node [
    id 43
    label "SOT_time_sales_D3"
    table_name "d3_sot_time_sales"
    type "SOT"
    semantic_name "time_sales"
    raw_name "time_sales"
    domain "product_catalog"
  ]
  node [
    id 44
    label "SPEC_catalog_performance_D3"
    table_name "d3_spec_catalog_performance"
    type "SPEC"
    semantic_name "catalog_performance"
    raw_name "catalog_performance"
    domain "product_catalog"
  ]
  node [
    id 45
    label "SPEC_store_sales_summary_D3"
    table_name "d3_spec_store_sales_summary"
    type "SPEC"
    semantic_name "store_sales_summary"
    raw_name "store_sales_summary"
    domain "product_catalog"
  ]
  node [
    id 46
    label "SPEC_time_analysis_D3"
    table_name "d3_spec_time_analysis"
    type "SPEC"
    semantic_name "time_analysis"
    raw_name "time_analysis"
    domain "product_catalog"
  ]
  node [
    id 47
    label "SPEC_warehouse_logistics_D3"
    table_name "d3_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
    domain "product_catalog"
  ]
  edge [
    source 0
    target 5
  ]
  edge [
    source 1
    target 6
  ]
  edge [
    source 1
    target 7
  ]
  edge [
    source 2
    target 4
  ]
  edge [
    source 2
    target 5
  ]
  edge [
    source 2
    target 6
  ]
  edge [
    source 3
    target 4
  ]
  edge [
    source 3
    target 7
  ]
  edge [
    source 4
    target 8
  ]
  edge [
    source 4
    target 9
  ]
  edge [
    source 4
    target 32
  ]
  edge [
    source 4
    target 44
  ]
  edge [
    source 5
    target 9
  ]
  edge [
    source 5
    target 10
  ]
  edge [
    source 5
    target 32
  ]
  edge [
    source 6
    target 11
  ]
  edge [
    source 8
    target 32
  ]
  edge [
    source 9
    target 10
  ]
  edge [
    source 10
    target 11
  ]
  edge [
    source 10
    target 32
  ]
  edge [
    source 12
    target 16
  ]
  edge [
    source 12
    target 17
  ]
  edge [
    source 12
    target 18
  ]
  edge [
    source 12
    target 19
  ]
  edge [
    source 13
    target 16
  ]
  edge [
    source 13
    target 19
  ]
  edge [
    source 15
    target 17
  ]
  edge [
    source 15
    target 18
  ]
  edge [
    source 16
    target 20
  ]
  edge [
    source 16
    target 21
  ]
  edge [
    source 17
    target 21
  ]
  edge [
    source 17
    target 23
  ]
  edge [
    source 19
    target 22
  ]
  edge [
    source 19
    target 23
  ]
  edge [
    source 21
    target 23
  ]
  edge [
    source 24
    target 28
  ]
  edge [
    source 24
    target 29
  ]
  edge [
    source 24
    target 31
  ]
  edge [
    source 25
    target 28
  ]
  edge [
    source 25
    target 30
  ]
  edge [
    source 26
    target 30
  ]
  edge [
    source 27
    target 29
  ]
  edge [
    source 27
    target 31
  ]
  edge [
    source 28
    target 33
  ]
  edge [
    source 28
    target 35
  ]
  edge [
    source 29
    target 46
  ]
  edge [
    source 30
    target 35
  ]
  edge [
    source 31
    target 46
  ]
  edge [
    source 33
    target 35
  ]
  edge [
    source 36
    target 41
  ]
  edge [
    source 36
    target 42
  ]
  edge [
    source 36
    target 43
  ]
  edge [
    source 37
    target 40
  ]
  edge [
    source 37
    target 41
  ]
  edge [
    source 37
    target 43
  ]
  edge [
    source 38
    target 40
  ]
  edge [
    source 38
    target 42
  ]
  edge [
    source 40
    target 34
  ]
  edge [
    source 41
    target 45
  ]
  edge [
    source 42
    target 45
  ]
  edge [
    source 42
    target 47
  ]
  edge [
    source 43
    target 34
  ]
  edge [
    source 45
    target 47
  ]
]
