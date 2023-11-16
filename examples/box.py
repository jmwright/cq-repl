import cadquery as cq

# Sample parameter
dim = 5.0

# Regular object definition
res = (
    cq.Workplane().box(dim, dim, dim)
)

# Be sure to evaluate the stand-alone plate function definition below first
res = plate()

# Alternatively, evaluate the class below and call this
# res = Plate.plate()

# This will be called implicitly, but can be called explicitly too
show_object(res)

# Stand-alone function for plate
def plate():
    res = cq.Workplane().circle(dim).extrude(3.0)

    return res


# plate function wrapped in a class
class Plate:
    def plate():
        res = cq.Workplane().circle(dim).extrude(3.0)

        return res
