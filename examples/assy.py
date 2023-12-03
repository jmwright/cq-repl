import cadquery as cq

# Create the first assembly object
box1 = cq.Workplane().box(10, 10, 10)
box2 = cq.Workplane().box(20, 10, 10)

# Create the base assembly
assy = cq.Assembly()
assy.add(box1, name="box1", color=cq.Color(1.0, 0.0, 0.0, 1.0))
assy.add(
    box2,
    name="box2",
    color=cq.Color(0.0, 0.0, 1.0, 1.0),
    loc=cq.Location((0.0, 20.0, 20.0)),
)

show_object(assy)

# Uncomment the lines below and send them to the repl to alter assembly component location/rotation and color
# assy.objects["box2"].loc = cq.Location((0, 0, 10), (1, 0, 1), 45)
# assy.objects["box2"].color = cq.Color(0, 1.0, 0, 1.0)
