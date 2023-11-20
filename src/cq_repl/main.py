import os, sys, select
from math import degrees
import time
import code

from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkRenderer,
    vtkRenderWindow,
    vtkPolyDataMapper as vtkMapper,
    vtkActor,
    vtkRenderWindowInteractor,
)
from vtkmodules.vtkFiltersExtraction import vtkExtractCellsByType
from vtkmodules.vtkCommonDataModel import VTK_TRIANGLE, VTK_LINE, VTK_VERTEX

import cadquery as cq

# VTK window and renderer
render_window = vtkRenderWindow()
renderer = vtkRenderer()

# Keeps track of all the objects that we are rendering so they can be updated
display_objects = {}


def process_assembly(assy):
    """
    Breaks an assembly down so that it can be displayed properly by the
    REPL mechanism.
    """

    objects = {}

    # Collect all of the shapes, along with their color, translation and rotation data
    for shape, name, loc, col in assy:
        color = col.toTuple() if col else (0.5, 0.5, 0.5, 1.0)
        trans, rot = loc.toTuple()

        # Lower level shapes need to be named and wrapped in a cq.Workplane object
        model = cq.Workplane(shape)
        model.label = name

        object = {"model": model, "color": color, "translation": trans, "rotation": rot}

        objects[name] = object

    return objects


def show_object(model):
    """
    Called by the CadQuery script to display an Assembly/Workplane object.
    """

    # Filter out dummy calls with None
    if model == None:
        return

    if type(model).__name__ == "Workplane":
        # Wrap the model in a dict to carry extra info with it
        objects = {}
        objects[model.label] = {
            "model": model,
            "color": (0.93, 0.46, 0.0, 1.0),
            "translation": (0, 0, 0),
            "rotation": (0, 0, 0),
        }
    elif type(model).__name__ == "Assembly":
        objects = process_assembly(model)

    # Step through all the objects and update them
    for name, object in objects.items():
        # Add face and edge related rendering objects to the renderer if they do not already exist
        if name not in display_objects:
            display_objects[name] = {
                "face_mapper": vtkMapper(),
                "face_actor": vtkActor(),
                "edge_mapper": vtkMapper(),
                "edge_actor": vtkActor(),
            }

            # Associate the actors and mappers
            display_objects[name]["face_actor"].SetMapper(
                display_objects[name]["face_mapper"]
            )
            renderer.AddActor(display_objects[name]["face_actor"])
            display_objects[name]["edge_actor"].SetMapper(
                display_objects[name]["edge_mapper"]
            )
            renderer.AddActor(display_objects[name]["edge_actor"])

        update_object(
            object["model"], object["color"], object["translation"], object["rotation"]
        )


def update_object(obj, color, translation, rotation):
    """
    Converts a Workplane object and adds its data to the VTK renderer.
    """

    data = obj.val().toVtkPolyData(1e-3, 0.1)

    # Extract faces
    extr = vtkExtractCellsByType()
    extr.SetInputDataObject(data)

    extr.AddCellType(VTK_LINE)
    extr.AddCellType(VTK_VERTEX)
    extr.Update()
    data_edges = extr.GetOutput()

    # Extract edges
    extr = vtkExtractCellsByType()
    extr.SetInputDataObject(data)

    extr.AddCellType(VTK_TRIANGLE)
    extr.Update()
    data_faces = extr.GetOutput()

    # Remove normals from edges
    data_edges.GetPointData().RemoveArray("Normals")

    # The name is based on the user-specified object label for now
    name = obj.label

    # Update the faces
    display_objects[name]["face_mapper"].SetInputDataObject(data_faces)
    display_objects[name]["face_actor"].SetPosition(*translation)
    display_objects[name]["face_actor"].SetOrientation(*map(degrees, rotation))
    display_objects[name]["face_actor"].GetProperty().SetColor(*color[:3])
    display_objects[name]["face_actor"].GetProperty().SetOpacity(color[3])

    # Update the edges
    display_objects[name]["edge_mapper"].SetInputDataObject(data_edges)
    display_objects[name]["edge_actor"].SetPosition(*translation)
    display_objects[name]["edge_actor"].SetOrientation(*map(degrees, rotation))
    display_objects[name]["edge_actor"].GetProperty().SetColor(0, 0, 0)
    display_objects[name]["edge_actor"].GetProperty().SetLineWidth(2)

    # Force an update
    renderer.Render()
    render_window.Render()


class replTimerCallback:
    """
    Holds the information necessary to present the REPL prompt to the user properly.
    """

    def __init__(self):
        self.buffer = ""
        self.command_incomplete = False
        self.open_count = 0
        self.close_count = 0

    def execute(self, obj, event):
        """
        Called periodically to accept REPL input from the user.
        """
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()

            # If the line is a comment, there is no reason to execute it
            if line.strip().startswith("#"):
                return

            # If the line starts with class or def, expect some indented lines
            if line.strip().startswith("def") or line.strip().startswith("class"):
                self.command_incomplete = True
                self.buffer += line
                return

            # See if a function is being closed out
            if line.strip().startswith("return"):
                self.buffer += line
                line = self.buffer

                # Reset back to the complete line condition
                self.command_incomplete = False
                self.buffer = ""

            # Check for follow-on indented lines
            if line.startswith(" ") and self.command_incomplete:
                self.buffer += line
                return

            if "(" in line or ")" in line:
                # Check if the line is incomplete (open parens do not match close perens)
                for i in line:
                    if i == "(":
                        self.open_count = self.open_count + 1
                    if i == ")":
                        self.close_count = self.close_count + 1
                if self.open_count != self.close_count:
                    self.command_incomplete = True
                    self.buffer += line
                    return

                # If we had an incomplete command before but it is complete now, finish it out
                if self.command_incomplete and self.open_count == self.close_count:
                    self.buffer += line
                    line = self.buffer

                    # Reset back to the complete line condition
                    self.command_incomplete = False
                    self.buffer = ""
                    self.open_count = 0
                    self.close_count = 0

            # Figure out if the line is code, or the user hitting Ctrl-D
            if line:
                # Run the line given by the user
                code_obj = code.compile_command(line)
                exec(code_obj, globals())

                # Make sure the user does not get a stray prompt when they hit enter to close something
                if not line.endswith(os.linesep + os.linesep) and line != os.linesep:
                    # Let the user know that we are ready for more input
                    print(">>> ", end="", flush=True)
            else:
                # The user hit Ctrl-D
                exit(0)

            # If the line contains an assignment, inject a label set
            if "=" in line and line.split(" ")[1] == "=":
                obj_name = line.split("=")[0].strip()
                code_obj = code.compile_command(f"{obj_name}.label='{obj_name}'")

                # Use a try in case we are trying to call show_object with something other than a CadQuery object
                try:
                    exec(code_obj, globals())
                except:
                    pass

                # Inject an automatic show_object call
                code_obj = code.compile_command(f"show_object({obj_name})")

                # Use a try in case we are trying to call show_object with something other than a CadQuery object
                try:
                    exec(code_obj, globals())
                except:
                    pass
            elif "show_object" not in line and "=" not in line:
                code_obj = code.compile_command(f"show_object(None)")
                exec(code_obj, globals())


def init_vtkwindow(render_window, renderer, repl_cb):
    """
    Sets up the VTK render window and displays a 3D model in it.
    """

    # VTK window
    render_window.AddRenderer(renderer)

    render_window.SetWindowName("cq-repl")

    # rendering related settings
    render_window.SetMultiSamples(16)
    vtkMapper.SetResolveCoincidentTopologyToPolygonOffset()
    vtkMapper.SetResolveCoincidentTopologyPolygonOffsetParameters(1, 0)
    vtkMapper.SetResolveCoincidentTopologyLineOffsetParameters(-1, 0)

    # VTK interactor
    interactor = vtkRenderWindowInteractor()
    interactor.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
    interactor.SetRenderWindow(render_window)

    # Axes indicator
    axes = vtkAxesActor()
    axes.SetDragable(0)
    tp = axes.GetXAxisCaptionActor2D().GetCaptionTextProperty()
    tp.SetColor(0, 0, 0)
    axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().ShallowCopy(tp)
    axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().ShallowCopy(tp)

    # Orientation widget
    orient_widget = vtkOrientationMarkerWidget()
    orient_widget.SetOrientationMarker(axes)
    orient_widget.SetViewport(0.9, 0.0, 1.0, 0.2)
    orient_widget.SetZoom(1.1)
    orient_widget.SetInteractor(interactor)
    orient_widget.EnabledOn()
    orient_widget.InteractiveOff()

    # Use gradient background
    renderer = render_window.GetRenderers().GetFirstRenderer()
    renderer.GradientBackgroundOn()

    # Camera setup
    camera = renderer.GetActiveCamera()
    camera.Roll(-35)
    camera.Elevation(-45)
    renderer.ResetCamera()

    # Set window dimensions
    interactor.Initialize()
    interactor.Enable()
    render_window.SetSize(800, 600)  # *win.GetScreenSize())
    render_window.SetPosition(-10, 0)

    # Timer to handle command line REPL input
    interactor.AddObserver("TimerEvent", repl_cb.execute)
    timerId = interactor.CreateRepeatingTimer(10)

    # show and return
    render_window.Render()
    interactor.Start()

    render_window.Finalize()
    render_window.GetInteractor().TerminateApp()


def main():
    # Let the user know we are ready for the next command
    print(">>> ", end="", flush=True)

    repl_cb = replTimerCallback()

    # Create and show the render window
    init_vtkwindow(render_window, renderer, repl_cb)


if __name__ == "__main__":
    main()
