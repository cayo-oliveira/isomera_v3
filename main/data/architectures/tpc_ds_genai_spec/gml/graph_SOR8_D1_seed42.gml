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
    label "SOR_customer_address_D1"
    table_name "d1_sor_customer_address"
    type "SOR"
    semantic_name "customer_address"
    raw_name "customer_address"
    domain "customer"
  ]
  node [
    id 2
    label "SOR_customer_demographics_D1"
    table_name "d1_sor_customer_demographics"
    type "SOR"
    semantic_name "customer_demographics"
    raw_name "customer_demographics"
    domain "customer"
  ]
  node [
    id 3
    label "SOR_extra_1_D1"
    table_name "d1_sor_loyalty_profile"
    type "SOR"
    semantic_name "loyalty_profile"
    raw_name "extra_1"
    domain "customer"
  ]
  node [
    id 4
    label "SOR_extra_2_D1"
    table_name "d1_sor_household_profile"
    type "SOR"
    semantic_name "household_profile"
    raw_name "extra_2"
    domain "customer"
  ]
  node [
    id 5
    label "SOR_extra_3_D1"
    table_name "d1_sor_customer_touchpoint"
    type "SOR"
    semantic_name "customer_touchpoint"
    raw_name "extra_3"
    domain "customer"
  ]
  node [
    id 6
    label "SOR_extra_4_D1"
    table_name "d1_sor_support_case"
    type "SOR"
    semantic_name "support_case"
    raw_name "extra_4"
    domain "customer"
  ]
  node [
    id 7
    label "SOR_extra_5_D1"
    table_name "d1_sor_digital_identity"
    type "SOR"
    semantic_name "digital_identity"
    raw_name "extra_5"
    domain "customer"
  ]
  node [
    id 8
    label "SOT_catalog_sales_D1"
    table_name "d1_sot_catalog_sales"
    type "SOT"
    semantic_name "catalog_sales"
    raw_name "catalog_sales"
    domain "customer"
  ]
  node [
    id 9
    label "SOT_customer_attr_D1"
    table_name "d1_sot_customer_attr"
    type "SOT"
    semantic_name "customer_attr"
    raw_name "customer_attr"
    domain "customer"
  ]
  node [
    id 10
    label "SOT_customer_orders_D1"
    table_name "d1_sot_customer_orders"
    type "SOT"
    semantic_name "customer_orders"
    raw_name "customer_orders"
    domain "customer"
  ]
  node [
    id 11
    label "SOT_store_sales_D1"
    table_name "d1_sot_store_sales"
    type "SOT"
    semantic_name "store_sales"
    raw_name "store_sales"
    domain "customer"
  ]
  node [
    id 12
    label "SOT_time_sales_D1"
    table_name "d1_sot_time_sales"
    type "SOT"
    semantic_name "time_sales"
    raw_name "time_sales"
    domain "customer"
  ]
  node [
    id 13
    label "SOT_warehouse_stock_D1"
    table_name "d1_sot_warehouse_stock"
    type "SOT"
    semantic_name "warehouse_stock"
    raw_name "warehouse_stock"
    domain "customer"
  ]
  node [
    id 14
    label "SOT_web_sales_D1"
    table_name "d1_sot_web_sales"
    type "SOT"
    semantic_name "web_sales"
    raw_name "web_sales"
    domain "customer"
  ]
  node [
    id 15
    label "SPEC_catalog_performance_D1"
    table_name "d1_spec_catalog_performance"
    type "SPEC"
    semantic_name "catalog_performance"
    raw_name "catalog_performance"
    domain "customer"
  ]
  node [
    id 16
    label "SPEC_customer_summary_D1"
    table_name "d1_spec_customer_summary"
    type "SPEC"
    semantic_name "customer_summary"
    raw_name "customer_summary"
    domain "customer"
  ]
  node [
    id 17
    label "SPEC_store_sales_summary_D1"
    table_name "d1_spec_store_sales_summary"
    type "SPEC"
    semantic_name "store_sales_summary"
    raw_name "store_sales_summary"
    domain "customer"
  ]
  node [
    id 18
    label "SPEC_time_analysis_D1"
    table_name "d1_spec_time_analysis"
    type "SPEC"
    semantic_name "time_analysis"
    raw_name "time_analysis"
    domain "customer"
  ]
  node [
    id 19
    label "SPEC_warehouse_logistics_D1"
    table_name "d1_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
    domain "customer"
  ]
  node [
    id 20
    label "SPEC_web_sales_summary_D1"
    table_name "d1_spec_web_sales_summary"
    type "SPEC"
    semantic_name "web_sales_summary"
    raw_name "web_sales_summary"
    domain "customer"
  ]
  edge [
    source 0
    target 9
  ]
  edge [
    source 0
    target 10
  ]
  edge [
    source 0
    target 11
  ]
  edge [
    source 0
    target 14
  ]
  edge [
    source 1
    target 8
  ]
  edge [
    source 1
    target 9
  ]
  edge [
    source 1
    target 12
  ]
  edge [
    source 1
    target 13
  ]
  edge [
    source 3
    target 8
  ]
  edge [
    source 4
    target 10
  ]
  edge [
    source 4
    target 13
  ]
  edge [
    source 5
    target 12
  ]
  edge [
    source 6
    target 11
  ]
  edge [
    source 7
    target 14
  ]
  edge [
    source 8
    target 15
  ]
  edge [
    source 8
    target 18
  ]
  edge [
    source 9
    target 15
  ]
  edge [
    source 9
    target 16
  ]
  edge [
    source 10
    target 16
  ]
  edge [
    source 10
    target 17
  ]
  edge [
    source 10
    target 20
  ]
  edge [
    source 11
    target 15
  ]
  edge [
    source 11
    target 17
  ]
  edge [
    source 11
    target 19
  ]
  edge [
    source 12
    target 18
  ]
  edge [
    source 13
    target 19
  ]
  edge [
    source 14
    target 18
  ]
  edge [
    source 14
    target 20
  ]
  edge [
    source 17
    target 16
  ]
  edge [
    source 17
    target 19
  ]
]
