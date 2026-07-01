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
    label "SPEC_customer_summary_D2"
    table_name "d2_spec_customer_summary"
    type "SPEC"
    semantic_name "customer_summary"
    raw_name "customer_summary"
    domain "location_store"
  ]
  node [
    id 9
    label "SPEC_store_sales_summary_D2"
    table_name "d2_spec_store_sales_summary"
    type "SPEC"
    semantic_name "store_sales_summary"
    raw_name "store_sales_summary"
    domain "location_store"
  ]
  node [
    id 10
    label "SPEC_warehouse_logistics_D2"
    table_name "d2_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
    domain "location_store"
  ]
  node [
    id 11
    label "SPEC_web_sales_summary_D2"
    table_name "d2_spec_web_sales_summary"
    type "SPEC"
    semantic_name "web_sales_summary"
    raw_name "web_sales_summary"
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
    target 20
  ]
  edge [
    source 5
    target 9
  ]
  edge [
    source 5
    target 11
  ]
  edge [
    source 5
    target 23
  ]
  edge [
    source 6
    target 10
  ]
  edge [
    source 7
    target 11
  ]
  edge [
    source 7
    target 22
  ]
  edge [
    source 7
    target 23
  ]
  edge [
    source 8
    target 9
  ]
  edge [
    source 8
    target 11
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
    target 8
  ]
  edge [
    source 16
    target 21
  ]
  edge [
    source 17
    target 8
  ]
  edge [
    source 17
    target 21
  ]
  edge [
    source 20
    target 8
  ]
  edge [
    source 20
    target 21
  ]
]
