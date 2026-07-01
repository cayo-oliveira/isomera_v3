graph [
  directed 1
  node [
    id 0
    label "SOR_customer_D1"
    table_name "d1_sor_customer"
    type "SOR"
    semantic_name "customer"
    raw_name "customer"
    domain "customer"
  ]
  node [
    id 1
    label "SOR_customer_demographics_D1"
    table_name "d1_sor_customer_demographics"
    type "SOR"
    semantic_name "customer_demographics"
    raw_name "customer_demographics"
    domain "customer"
  ]
  node [
    id 2
    label "SOT_time_sales_D1"
    table_name "d1_sot_time_sales"
    type "SOT"
    semantic_name "time_sales"
    raw_name "time_sales"
    domain "customer"
  ]
  node [
    id 3
    label "SOT_warehouse_stock_D1"
    table_name "d1_sot_warehouse_stock"
    type "SOT"
    semantic_name "warehouse_stock"
    raw_name "warehouse_stock"
    domain "customer"
  ]
  node [
    id 4
    label "SPEC_catalog_performance_D1"
    table_name "d1_spec_catalog_performance"
    type "SPEC"
    semantic_name "catalog_performance"
    raw_name "catalog_performance"
    domain "customer"
  ]
  node [
    id 5
    label "SPEC_warehouse_logistics_D1"
    table_name "d1_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
    domain "customer"
  ]
  node [
    id 6
    label "SOR_date_dim_D4"
    table_name "d4_sor_date_dim"
    type "SOR"
    semantic_name "date_dim"
    raw_name "date_dim"
    domain "date_time"
  ]
  node [
    id 7
    label "SOR_time_dim_D4"
    table_name "d4_sor_time_dim"
    type "SOR"
    semantic_name "time_dim"
    raw_name "time_dim"
    domain "date_time"
  ]
  node [
    id 8
    label "SOT_customer_orders_D4"
    table_name "d4_sot_customer_orders"
    type "SOT"
    semantic_name "customer_orders"
    raw_name "customer_orders"
    domain "date_time"
  ]
  node [
    id 9
    label "SOT_warehouse_stock_D4"
    table_name "d4_sot_warehouse_stock"
    type "SOT"
    semantic_name "warehouse_stock"
    raw_name "warehouse_stock"
    domain "date_time"
  ]
  node [
    id 10
    label "SPEC_customer_summary_D4"
    table_name "d4_spec_customer_summary"
    type "SPEC"
    semantic_name "customer_summary"
    raw_name "customer_summary"
    domain "date_time"
  ]
  node [
    id 11
    label "SPEC_warehouse_logistics_D4"
    table_name "d4_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
    domain "date_time"
  ]
  node [
    id 12
    label "SOR_income_band_D5"
    table_name "d5_sor_income_band"
    type "SOR"
    semantic_name "income_band"
    raw_name "income_band"
    domain "logistics_fulfillment"
  ]
  node [
    id 13
    label "SOR_warehouse_D5"
    table_name "d5_sor_warehouse"
    type "SOR"
    semantic_name "warehouse"
    raw_name "warehouse"
    domain "logistics_fulfillment"
  ]
  node [
    id 14
    label "SOT_customer_orders_D5"
    table_name "d5_sot_customer_orders"
    type "SOT"
    semantic_name "customer_orders"
    raw_name "customer_orders"
    domain "logistics_fulfillment"
  ]
  node [
    id 15
    label "SOT_store_sales_D5"
    table_name "d5_sot_store_sales"
    type "SOT"
    semantic_name "store_sales"
    raw_name "store_sales"
    domain "logistics_fulfillment"
  ]
  node [
    id 16
    label "SPEC_customer_summary_D5"
    table_name "d5_spec_customer_summary"
    type "SPEC"
    semantic_name "customer_summary"
    raw_name "customer_summary"
    domain "logistics_fulfillment"
  ]
  node [
    id 17
    label "SPEC_store_sales_summary_D5"
    table_name "d5_spec_store_sales_summary"
    type "SPEC"
    semantic_name "store_sales_summary"
    raw_name "store_sales_summary"
    domain "logistics_fulfillment"
  ]
  node [
    id 18
    label "SOR_item_D3"
    table_name "d3_sor_item"
    type "SOR"
    semantic_name "item"
    raw_name "item"
    domain "product_catalog"
  ]
  node [
    id 19
    label "SOR_promotion_D3"
    table_name "d3_sor_promotion"
    type "SOR"
    semantic_name "promotion"
    raw_name "promotion"
    domain "product_catalog"
  ]
  node [
    id 20
    label "SOT_catalog_sales_D3"
    table_name "d3_sot_catalog_sales"
    type "SOT"
    semantic_name "catalog_sales"
    raw_name "catalog_sales"
    domain "product_catalog"
  ]
  node [
    id 21
    label "SOT_customer_orders_D3"
    table_name "d3_sot_customer_orders"
    type "SOT"
    semantic_name "customer_orders"
    raw_name "customer_orders"
    domain "product_catalog"
  ]
  node [
    id 22
    label "SPEC_time_analysis_D3"
    table_name "d3_spec_time_analysis"
    type "SPEC"
    semantic_name "time_analysis"
    raw_name "time_analysis"
    domain "product_catalog"
  ]
  node [
    id 23
    label "SPEC_warehouse_logistics_D3"
    table_name "d3_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
    domain "product_catalog"
  ]
  node [
    id 24
    label "SOR_nation_D2"
    table_name "d2_sor_nation"
    type "SOR"
    semantic_name "nation"
    raw_name "nation"
    domain "location_store"
  ]
  node [
    id 25
    label "SOR_store_D2"
    table_name "d2_sor_store"
    type "SOR"
    semantic_name "store"
    raw_name "store"
    domain "location_store"
  ]
  node [
    id 26
    label "SOT_customer_attr_D2"
    table_name "d2_sot_customer_attr"
    type "SOT"
    semantic_name "customer_attr"
    raw_name "customer_attr"
    domain "location_store"
  ]
  node [
    id 27
    label "SOT_customer_orders_D2"
    table_name "d2_sot_customer_orders"
    type "SOT"
    semantic_name "customer_orders"
    raw_name "customer_orders"
    domain "location_store"
  ]
  node [
    id 28
    label "SPEC_customer_summary_D2"
    table_name "d2_spec_customer_summary"
    type "SPEC"
    semantic_name "customer_summary"
    raw_name "customer_summary"
    domain "location_store"
  ]
  node [
    id 29
    label "SPEC_time_analysis_D2"
    table_name "d2_spec_time_analysis"
    type "SPEC"
    semantic_name "time_analysis"
    raw_name "time_analysis"
    domain "location_store"
  ]
  edge [
    source 0
    target 2
  ]
  edge [
    source 0
    target 3
  ]
  edge [
    source 1
    target 2
  ]
  edge [
    source 1
    target 3
  ]
  edge [
    source 2
    target 4
  ]
  edge [
    source 3
    target 5
  ]
  edge [
    source 6
    target 8
  ]
  edge [
    source 6
    target 9
  ]
  edge [
    source 7
    target 8
  ]
  edge [
    source 7
    target 9
  ]
  edge [
    source 8
    target 10
  ]
  edge [
    source 8
    target 28
  ]
  edge [
    source 9
    target 29
  ]
  edge [
    source 12
    target 14
  ]
  edge [
    source 12
    target 15
  ]
  edge [
    source 13
    target 14
  ]
  edge [
    source 13
    target 15
  ]
  edge [
    source 14
    target 16
  ]
  edge [
    source 14
    target 17
  ]
  edge [
    source 15
    target 17
  ]
  edge [
    source 17
    target 16
  ]
  edge [
    source 18
    target 20
  ]
  edge [
    source 18
    target 21
  ]
  edge [
    source 19
    target 20
  ]
  edge [
    source 19
    target 21
  ]
  edge [
    source 20
    target 22
  ]
  edge [
    source 20
    target 23
  ]
  edge [
    source 21
    target 11
  ]
  edge [
    source 24
    target 26
  ]
  edge [
    source 24
    target 27
  ]
  edge [
    source 25
    target 26
  ]
  edge [
    source 25
    target 27
  ]
]
