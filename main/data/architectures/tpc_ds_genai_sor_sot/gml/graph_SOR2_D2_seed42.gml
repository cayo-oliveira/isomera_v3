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
    label "SOT_store_sales_D1"
    type "SOT"
  ]
  node [
    id 5
    label "SOT_customer_orders_D1"
    type "SOT"
  ]
  node [
    id 6
    label "SOT_web_sales_D2"
    type "SOT"
  ]
  node [
    id 7
    label "SOT_catalog_sales_D2"
    type "SOT"
  ]
  node [
    id 8
    label "SPEC_store_sales_summary_D1"
    type "SPEC"
  ]
  node [
    id 9
    label "SPEC_time_analysis_D1"
    type "SPEC"
  ]
  node [
    id 10
    label "SPEC_store_sales_summary_D2"
    type "SPEC"
  ]
  node [
    id 11
    label "SPEC_web_sales_summary_D2"
    type "SPEC"
  ]
  edge [
    source 4
    target 0
  ]
  edge [
    source 4
    target 1
  ]
  edge [
    source 5
    target 0
  ]
  edge [
    source 5
    target 1
  ]
  edge [
    source 6
    target 2
  ]
  edge [
    source 6
    target 3
  ]
  edge [
    source 7
    target 2
  ]
  edge [
    source 7
    target 3
  ]
  edge [
    source 8
    target 4
  ]
  edge [
    source 8
    target 5
  ]
  edge [
    source 9
    target 7
  ]
  edge [
    source 10
    target 4
  ]
  edge [
    source 11
    target 6
  ]
]
