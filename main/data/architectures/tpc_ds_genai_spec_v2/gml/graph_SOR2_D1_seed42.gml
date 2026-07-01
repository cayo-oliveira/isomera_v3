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
    source 4
    target 5
  ]
]
