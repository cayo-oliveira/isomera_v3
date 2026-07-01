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
    label "SOT_customer_attr_D1"
    table_name "d1_sot_customer_attr"
    type "SOT"
    semantic_name "customer_attr"
    raw_name "customer_attr"
    domain "customer"
  ]
  node [
    id 3
    label "SOT_time_sales_D1"
    table_name "d1_sot_time_sales"
    type "SOT"
    semantic_name "time_sales"
    raw_name "time_sales"
    domain "customer"
  ]
  node [
    id 4
    label "SPEC_store_sales_summary_D1"
    table_name "d1_spec_store_sales_summary"
    type "SPEC"
    semantic_name "store_sales_summary"
    raw_name "store_sales_summary"
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
    label "SOT_customer_attr_D4"
    table_name "d4_sot_customer_attr"
    type "SOT"
    semantic_name "customer_attr"
    raw_name "customer_attr"
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
    label "SPEC_store_sales_summary_D4"
    table_name "d4_spec_store_sales_summary"
    type "SPEC"
    semantic_name "store_sales_summary"
    raw_name "store_sales_summary"
    domain "date_time"
  ]
  node [
    id 11
    label "SPEC_time_analysis_D4"
    table_name "d4_spec_time_analysis"
    type "SPEC"
    semantic_name "time_analysis"
    raw_name "time_analysis"
    domain "date_time"
  ]
  node [
    id 12
    label "SOR_item_D3"
    table_name "d3_sor_item"
    type "SOR"
    semantic_name "item"
    raw_name "item"
    domain "product_catalog"
  ]
  node [
    id 13
    label "SOR_promotion_D3"
    table_name "d3_sor_promotion"
    type "SOR"
    semantic_name "promotion"
    raw_name "promotion"
    domain "product_catalog"
  ]
  node [
    id 14
    label "SOT_customer_orders_D3"
    table_name "d3_sot_customer_orders"
    type "SOT"
    semantic_name "customer_orders"
    raw_name "customer_orders"
    domain "product_catalog"
  ]
  node [
    id 15
    label "SOT_web_sales_D3"
    table_name "d3_sot_web_sales"
    type "SOT"
    semantic_name "web_sales"
    raw_name "web_sales"
    domain "product_catalog"
  ]
  node [
    id 16
    label "SPEC_warehouse_logistics_D3"
    table_name "d3_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
    domain "product_catalog"
  ]
  node [
    id 17
    label "SPEC_web_sales_summary_D3"
    table_name "d3_spec_web_sales_summary"
    type "SPEC"
    semantic_name "web_sales_summary"
    raw_name "web_sales_summary"
    domain "product_catalog"
  ]
  node [
    id 18
    label "SOR_nation_D2"
    table_name "d2_sor_nation"
    type "SOR"
    semantic_name "nation"
    raw_name "nation"
    domain "location_store"
  ]
  node [
    id 19
    label "SOR_store_D2"
    table_name "d2_sor_store"
    type "SOR"
    semantic_name "store"
    raw_name "store"
    domain "location_store"
  ]
  node [
    id 20
    label "SOT_customer_attr_D2"
    table_name "d2_sot_customer_attr"
    type "SOT"
    semantic_name "customer_attr"
    raw_name "customer_attr"
    domain "location_store"
  ]
  node [
    id 21
    label "SOT_warehouse_stock_D2"
    table_name "d2_sot_warehouse_stock"
    type "SOT"
    semantic_name "warehouse_stock"
    raw_name "warehouse_stock"
    domain "location_store"
  ]
  node [
    id 22
    label "SPEC_catalog_performance_D2"
    table_name "d2_spec_catalog_performance"
    type "SPEC"
    semantic_name "catalog_performance"
    raw_name "catalog_performance"
    domain "location_store"
  ]
  node [
    id 23
    label "SPEC_warehouse_logistics_D2"
    table_name "d2_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
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
    target 5
  ]
  edge [
    source 3
    target 11
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
    source 9
    target 16
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
    target 4
  ]
  edge [
    source 14
    target 17
  ]
  edge [
    source 15
    target 10
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
    source 21
    target 23
  ]
]
