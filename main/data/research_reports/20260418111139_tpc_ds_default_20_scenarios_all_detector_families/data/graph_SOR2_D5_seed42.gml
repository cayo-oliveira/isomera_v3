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
    label "SOR_income_band_D5"
    type "SOR"
  ]
  node [
    id 9
    label "SOR_warehouse_D5"
    type "SOR"
  ]
  node [
    id 10
    label "SOT_time_sales_D1"
    type "SOT"
  ]
  node [
    id 11
    label "SOT_warehouse_stock_D1"
    type "SOT"
  ]
  node [
    id 12
    label "SOT_customer_attr_D2"
    type "SOT"
  ]
  node [
    id 13
    label "SOT_customer_orders_D2"
    type "SOT"
  ]
  node [
    id 14
    label "SOT_customer_orders_D3"
    type "SOT"
  ]
  node [
    id 15
    label "SOT_catalog_sales_D3"
    type "SOT"
  ]
  node [
    id 16
    label "SOT_warehouse_stock_D4"
    type "SOT"
  ]
  node [
    id 17
    label "SOT_customer_orders_D4"
    type "SOT"
  ]
  node [
    id 18
    label "SOT_customer_orders_D5"
    type "SOT"
  ]
  node [
    id 19
    label "SOT_store_sales_D5"
    type "SOT"
  ]
  node [
    id 20
    label "SPEC_catalog_performance_D1"
    type "SPEC"
  ]
  node [
    id 21
    label "SPEC_warehouse_logistics_D1"
    type "SPEC"
  ]
  node [
    id 22
    label "SPEC_time_analysis_D2"
    type "SPEC"
  ]
  node [
    id 23
    label "SPEC_customer_summary_D2"
    type "SPEC"
  ]
  node [
    id 24
    label "SPEC_warehouse_logistics_D3"
    type "SPEC"
  ]
  node [
    id 25
    label "SPEC_time_analysis_D3"
    type "SPEC"
  ]
  node [
    id 26
    label "SPEC_warehouse_logistics_D4"
    type "SPEC"
  ]
  node [
    id 27
    label "SPEC_customer_summary_D4"
    type "SPEC"
  ]
  node [
    id 28
    label "SPEC_store_sales_summary_D5"
    type "SPEC"
  ]
  node [
    id 29
    label "SPEC_customer_summary_D5"
    type "SPEC"
  ]
  edge [
    source 10
    target 0
  ]
  edge [
    source 10
    target 1
  ]
  edge [
    source 11
    target 0
  ]
  edge [
    source 11
    target 1
  ]
  edge [
    source 12
    target 2
  ]
  edge [
    source 12
    target 3
  ]
  edge [
    source 13
    target 2
  ]
  edge [
    source 13
    target 3
  ]
  edge [
    source 14
    target 5
  ]
  edge [
    source 14
    target 4
  ]
  edge [
    source 15
    target 5
  ]
  edge [
    source 15
    target 4
  ]
  edge [
    source 16
    target 7
  ]
  edge [
    source 16
    target 6
  ]
  edge [
    source 17
    target 7
  ]
  edge [
    source 17
    target 6
  ]
  edge [
    source 18
    target 8
  ]
  edge [
    source 18
    target 9
  ]
  edge [
    source 19
    target 9
  ]
  edge [
    source 19
    target 8
  ]
  edge [
    source 20
    target 10
  ]
  edge [
    source 21
    target 11
  ]
  edge [
    source 22
    target 16
  ]
  edge [
    source 23
    target 17
  ]
  edge [
    source 24
    target 15
  ]
  edge [
    source 25
    target 15
  ]
  edge [
    source 26
    target 14
  ]
  edge [
    source 27
    target 17
  ]
  edge [
    source 28
    target 19
  ]
  edge [
    source 28
    target 18
  ]
  edge [
    source 29
    target 18
  ]
  edge [
    source 29
    target 28
  ]
]
