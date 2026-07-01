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
    label "SOT_customer_orders_D1"
    table_name "d1_sot_customer_orders"
    type "SOT"
    semantic_name "customer_orders"
    raw_name "customer_orders"
    domain "customer"
  ]
  node [
    id 3
    label "SOT_store_sales_D1"
    table_name "d1_sot_store_sales"
    type "SOT"
    semantic_name "store_sales"
    raw_name "store_sales"
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
    label "SPEC_time_analysis_D1"
    table_name "d1_spec_time_analysis"
    type "SPEC"
    semantic_name "time_analysis"
    raw_name "time_analysis"
    domain "customer"
  ]
  node [
    id 6
    label "SOR_nation_D2"
    table_name "d2_sor_nation"
    type "SOR"
    semantic_name "nation"
    raw_name "nation"
    domain "location_store"
  ]
  node [
    id 7
    label "SOR_store_D2"
    table_name "d2_sor_store"
    type "SOR"
    semantic_name "store"
    raw_name "store"
    domain "location_store"
  ]
  node [
    id 8
    label "SOT_catalog_sales_D2"
    table_name "d2_sot_catalog_sales"
    type "SOT"
    semantic_name "catalog_sales"
    raw_name "catalog_sales"
    domain "location_store"
  ]
  node [
    id 9
    label "SOT_web_sales_D2"
    table_name "d2_sot_web_sales"
    type "SOT"
    semantic_name "web_sales"
    raw_name "web_sales"
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
    label "SPEC_web_sales_summary_D2"
    table_name "d2_spec_web_sales_summary"
    type "SPEC"
    semantic_name "web_sales_summary"
    raw_name "web_sales_summary"
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
    target 4
  ]
  edge [
    source 3
    target 10
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
    target 5
  ]
  edge [
    source 9
    target 11
  ]
]
