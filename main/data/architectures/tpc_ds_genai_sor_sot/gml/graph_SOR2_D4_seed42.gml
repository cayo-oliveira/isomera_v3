graph [
  directed 1
  node [
    id 0
    label "SOR_customer_demographics_D1"
    type "SOR"
  ]
  node [
    id 1
    label "SOR_customer_D1"
    type "SOR"
  ]
  node [
    id 2
    label "SOR_store_D2"
    type "SOR"
  ]
  node [
    id 3
    label "SOR_nation_D2"
    type "SOR"
  ]
  node [
    id 4
    label "SOR_promotion_D3"
    type "SOR"
  ]
  node [
    id 5
    label "SOR_item_D3"
    type "SOR"
  ]
  node [
    id 6
    label "SOR_date_dim_D4"
    type "SOR"
  ]
  node [
    id 7
    label "SOR_time_dim_D4"
    type "SOR"
  ]
  node [
    id 8
    label "SOT_time_sales_D1"
    type "SOT"
  ]
  node [
    id 9
    label "SOT_customer_attr_D1"
    type "SOT"
  ]
  node [
    id 10
    label "SOT_customer_attr_D2"
    type "SOT"
  ]
  node [
    id 11
    label "SOT_warehouse_stock_D2"
    type "SOT"
  ]
  node [
    id 12
    label "SOT_web_sales_D3"
    type "SOT"
  ]
  node [
    id 13
    label "SOT_customer_orders_D3"
    type "SOT"
  ]
  node [
    id 14
    label "SOT_warehouse_stock_D4"
    type "SOT"
  ]
  node [
    id 15
    label "SOT_customer_attr_D4"
    type "SOT"
  ]
  node [
    id 16
    label "SPEC_store_sales_summary_D1"
    type "SPEC"
  ]
  node [
    id 17
    label "SPEC_warehouse_logistics_D1"
    type "SPEC"
  ]
  node [
    id 18
    label "SPEC_catalog_performance_D2"
    type "SPEC"
  ]
  node [
    id 19
    label "SPEC_warehouse_logistics_D2"
    type "SPEC"
  ]
  node [
    id 20
    label "SPEC_warehouse_logistics_D3"
    type "SPEC"
  ]
  node [
    id 21
    label "SPEC_web_sales_summary_D3"
    type "SPEC"
  ]
  node [
    id 22
    label "SPEC_time_analysis_D4"
    type "SPEC"
  ]
  node [
    id 23
    label "SPEC_store_sales_summary_D4"
    type "SPEC"
  ]
  edge [
    source 8
    target 0
  ]
  edge [
    source 8
    target 1
  ]
  edge [
    source 9
    target 1
  ]
  edge [
    source 9
    target 0
  ]
  edge [
    source 10
    target 2
  ]
  edge [
    source 10
    target 3
  ]
  edge [
    source 11
    target 2
  ]
  edge [
    source 11
    target 3
  ]
  edge [
    source 12
    target 5
  ]
  edge [
    source 12
    target 4
  ]
  edge [
    source 13
    target 5
  ]
  edge [
    source 13
    target 4
  ]
  edge [
    source 14
    target 6
  ]
  edge [
    source 14
    target 7
  ]
  edge [
    source 15
    target 7
  ]
  edge [
    source 15
    target 6
  ]
  edge [
    source 16
    target 13
  ]
  edge [
    source 17
    target 9
  ]
  edge [
    source 18
    target 10
  ]
  edge [
    source 19
    target 11
  ]
  edge [
    source 20
    target 14
  ]
  edge [
    source 21
    target 13
  ]
  edge [
    source 22
    target 8
  ]
  edge [
    source 23
    target 12
  ]
]
