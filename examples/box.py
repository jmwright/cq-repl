import cadquery as cq
dim = 5.0
res = (
    cq.Workplane().box(dim, dim, dim)
)
res = cq.Workplane().circle(dim).extrude(10.0)
show_object(res)