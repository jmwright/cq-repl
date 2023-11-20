import cadquery as cq

# Create the first assembly object
box1 = cq.Workplane().box(10, 10, 10)

# Create the base assembly
assy = cq.Assembly()
assy.add(box1, name="box1", color=cq.Color(1.0, 0.0, 0.0, 1.0))

show_object(assy)
