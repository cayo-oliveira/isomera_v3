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
    label "SOT_customer_attr_D1"
    table_name "d1_sot_customer_attr"
    type "SOT"
    semantic_name "customer_attr"
    raw_name "customer_attr"
    domain "customer"
  ]
  node [
    id 5
    label "SOT_store_sales_D1"
    table_name "d1_sot_store_sales"
    type "SOT"
    semantic_name "store_sales"
    raw_name "store_sales"
    domain "customer"
  ]
  node [
    id 6
    label "SOT_time_sales_D1"
    table_name "d1_sot_time_sales"
    type "SOT"
    semantic_name "time_sales"
    raw_name "time_sales"
    domain "customer"
  ]
  node [
    id 7
    label "SOT_warehouse_stock_D1"
    table_name "d1_sot_warehouse_stock"
    type "SOT"
    semantic_name "warehouse_stock"
    raw_name "warehouse_stock"
    domain "customer"
  ]
  node [
    id 8
    label "SPEC_catalog_performance_D1"
    table_name "d1_spec_catalog_performance"
    type "SPEC"
    semantic_name "catalog_performance"
    raw_name "catalog_performance"
    domain "customer"
  ]
  node [
    id 9
    label "SPEC_customer_summary_D1"
    table_name "d1_spec_customer_summary"
    type "SPEC"
    semantic_name "customer_summary"
    raw_name "customer_summary"
    domain "customer"
  ]
  node [
    id 10
    label "SPEC_time_analysis_D1"
    table_name "d1_spec_time_analysis"
    type "SPEC"
    semantic_name "time_analysis"
    raw_name "time_analysis"
    domain "customer"
  ]
  node [
    id 11
    label "SPEC_warehouse_logistics_D1"
    table_name "d1_spec_warehouse_logistics"
    type "SPEC"
    semantic_name "warehouse_logistics"
    raw_name "warehouse_logistics"
    domain "customer"
  ]
  edge [
    source 0
    target 4
  ]
  edge [
    source 0
    target 5
  ]
  edge [
    source 0
    target 6
  ]
  edge [
    source 1
    target 4
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
    target 5
  ]
  edge [
    source 2
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
    source 5
    target 8
  ]
  edge [
    source 5
    target 11
  ]
  edge [
    source 6
    target 10
  ]
  edge [
    source 7
    target 11
  ]
]
