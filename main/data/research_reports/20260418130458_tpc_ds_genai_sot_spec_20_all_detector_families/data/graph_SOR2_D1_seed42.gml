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
    label "SOT_customer_attr_D1"
    type "SOT"
  ]
  node [
    id 3
    label "SOT_time_sales_D1"
    type "SOT"
  ]
  node [
    id 4
    label "SPEC_store_sales_summary_D1"
    type "SPEC"
  ]
  node [
    id 5
    label "SPEC_warehouse_logistics_D1"
    type "SPEC"
  ]
  edge [
    source 2
    target 1
  ]
  edge [
    source 2
    target 0
  ]
  edge [
    source 3
    target 1
  ]
  edge [
    source 3
    target 0
  ]
  edge [
    source 4
    target 2
  ]
  edge [
    source 5
    target 4
  ]
]
