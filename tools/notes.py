import bpy
import bgl
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from gpu.types import GPUBatch, GPUOffScreen
import os
import json
import time

import json
import os
import uuid


# Edit note operator
class NODESHELF_OT_rename_note(bpy.types.Operator):
    bl_idname = "nodeshelf.rename_note"
    bl_label = "Rename Note"
    bl_options = {"REGISTER", "UNDO"}

    # Implement the invoke function
    def execute(self, context):
        nodeshelf_props = context.scene.nodeshelf_props
        note_input = nodeshelf_props.note_input
        ns_prefs = bpy.context.preferences.addons['NodeShelf'].preferences
        data_folder = ns_prefs.data_folder
        notesFolder = os.path.join(data_folder, f"NotesFolder")
        js = os.path.join(notesFolder, f"{bpy.context.space_data.node_tree.name}_Notes.json")
        dns = bpy.app.driver_namespace
        active_note = dns.get('active_note')

        new_note_text = note_input

        with open(js, 'r') as f:
            notes = [json.loads(line) for line in f]

        for note in notes:
            if note["id"] == active_note['id']:
                note["note"] = new_note_text
                break

        with open(js, 'w') as f:
            for note in notes:
                f.write(json.dumps(note) + '\n')

        dns["note_alert"] = True

        return {"FINISHED"}


def read_json(js):
    with open(js, 'r') as f:
        notes = [json.loads(line) for line in f]
    return notes

def write_to_json(js, notes):
    with open(js, 'w') as f:
        for note in notes:
            f.write(json.dumps(note) + '\n')

# Remove note operator
class NODESHELF_OT_remove_note(bpy.types.Operator):
    bl_idname = "nodeshelf.remove_note"
    bl_label = "Remove Note"
    bl_options = {"REGISTER", "UNDO"}

    # Implement the invoke function
    def execute(self, context):
        nodeshelf_props = context.scene.nodeshelf_props
        ns_prefs = bpy.context.preferences.addons['NodeShelf'].preferences
        data_folder = ns_prefs.data_folder
        notesFolder = os.path.join(data_folder, f"NotesFolder")
        js = os.path.join(notesFolder, f"{bpy.context.space_data.node_tree.name}_Notes.json")
        dns = bpy.app.driver_namespace
        selected_notes = dns.get('selected_notes')
        active_note = dns.get('active_note')
        if active_note:
            notes = read_json(js)
            new_notes = [n for n in notes if (n["id"] != active_note['id'])]
            write_to_json(js, new_notes)
        if selected_notes:
            for note in selected_notes:
                note_id = note['id']
                notes = read_json(js)
                new_notes = [note for note in notes if (note["id"] != note_id)]
                write_to_json(js, new_notes)


        dns["note_alert"] = True

        return {"FINISHED"}


# Duplicate note operator
class NODESHELF_OT_duplicate_note(bpy.types.Operator):
    bl_idname = "nodeshelf.duplicate_note"
    bl_label = "Duplicate Note"
    bl_options = {"REGISTER", "UNDO"}

    # Implement the invoke function
    def execute(self, context):
        nodeshelf_props = context.scene.nodeshelf_props
        show_notes = nodeshelf_props.show_notes
        ns_prefs = bpy.context.preferences.addons['NodeShelf'].preferences
        data_folder = ns_prefs.data_folder
        notesFolder = os.path.join(data_folder, f"NotesFolder")
        js = os.path.join(notesFolder, f"{bpy.context.space_data.node_tree.name}_Notes.json")
        dns = bpy.app.driver_namespace
        active_note = dns.get('active_note')
        ###

        with open(js, 'r') as f:
            notes = [json.loads(line) for line in f]

        for note in notes:
            if note["id"] == active_note['id']:
                new_note = note.copy()
                new_note["id"] = str(uuid.uuid4())
                new_note["coordinates"] = [coord + 10 for coord in new_note["coordinates"]]
                new_note['is_linked'] = False
                notes.append(new_note)
                break

        with open(js, 'w') as f:
            for note in notes:
                f.write(json.dumps(note) + '\n')

        dns['active_note'] = new_note
        dns["note_alert"] = True

        return {"FINISHED"}


class NODESHELF_OT_open_json(bpy.types.Operator):
    bl_idname = "nodeshelf.open_json"
    bl_label = "Open Json"

    def execute(self, context):
        pass
        return {"FINISHED"}

class NoteWidget:
    def __init__(self, id, note, color, coordinates, is_linked, linked_node):
        self.id = id
        self.note = note
        self.color = color
        self.coordinates = coordinates
        self.is_linked = is_linked
        self.linked_node = linked_node

    def serialize(self):
        return {
            "id": self.id,
            "note": self.note,
            "color": tuple(self.color),
            "coordinates": self.coordinates,
            "is_linked": self.is_linked,
            "linked_node": self.linked_node,
        }


class NODESHELF_OT_add_note(bpy.types.Operator):
    bl_idname = "nodeshelf.add_note"
    bl_label = "Add Note"
    #This operator bascially just adds a new note entry to the json
    #it draws temporary widget to visualize the placement of the note
    #the real drawing happens with the manage notes operator
    base_zoom_level: bpy.props.FloatProperty()

    def __init__(self):
        self.rect_x = 0
        self.rect_y = 0
        self.fixed = False
        nodeshelf_props = bpy.context.scene.nodeshelf_props
        ns_prefs = bpy.context.preferences.addons['NodeShelf'].preferences
        self.data_folder = ns_prefs.data_folder
        self.note = nodeshelf_props.note_input
        self.note_color = nodeshelf_props.note_color
        self.base_font_size = ns_prefs.font_size
        self.border_color = ns_prefs.border_color

    def draw_callback_px(self, context, args):
        # Calculate the size of one pixel in view coordinates
        px_x, px_y = bpy.context.region.view2d.region_to_view(1, 1)
        zero_x, zero_y = bpy.context.region.view2d.region_to_view(0, 0)
        pixel_size_x = px_x - zero_x
        pixel_size_y = px_y - zero_y

        # Scale font size from base zoom level (getting proportions of zoom)
        font_size = self.base_font_size / pixel_size_x * 0.75
        # Draw the note text
        font_id = 0  # default Blender font

        # Set the font size before getting dimensions
        blf.size(font_id, int(font_size), 72)  # font size

        # Calculate the length of the note text
        text_width_pixel, _ = blf.dimensions(font_id, self.note)
        text_width_view = text_width_pixel / pixel_size_x  # Convert to view coordinates

        # Calculate rectangle and triangle dimensions
        width = (text_width_pixel+15)/2   # Use text width as rectangle width
        height = 20 / pixel_size_y
        triangle_height = 10 / pixel_size_y
        triangle_half_width = 10 / pixel_size_x

        # Convert view space coordinates back to region space for drawing
        self.rect_x, self.rect_y = bpy.context.region.view2d.view_to_region(self.mx, self.my)
        # Adjust text position for centered alignment
        text_position_x = self.rect_x - text_width_pixel / 2



        # Draw larger shapes (to serve as borders)
        border_vertices = (
            (self.rect_x - width - 1, self.rect_y + triangle_height+height + 1), ### TOP LEFT VERT
            (self.rect_x - width - 1, self.rect_y + triangle_height - 1), ### BOTTOM LEFT VERT
            (self.rect_x + width + 1, self.rect_y + triangle_height - 1), ### BOTTOM RIGHT VERT
            (self.rect_x + width + 1, self.rect_y + triangle_height+height + 1), ### TOP RIGHT VERT

            # Triangle vertices
            (self.rect_x - triangle_half_width - 1, self.rect_y + triangle_height + 1), ### Top left
            (self.rect_x + triangle_half_width + 2, self.rect_y + triangle_height + 1), ### Top Right
            (self.rect_x, self.rect_y - 1) ### Bottom vert
        )
        indices = ((0, 1, 2), (2, 3, 0), (4, 5, 6))
        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        border_batch = batch_for_shader(shader, 'TRIS', {"pos": border_vertices}, indices=indices)
        shader.bind()

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        shader.uniform_float("color", (self.border_color[0], self.border_color[1], self.border_color[2], self.note_color[3]))  # RGBA white color
        border_batch.draw(shader)
        bgl.glDisable(bgl.GL_BLEND)
        # Draw main shapes
        main_vertices = (
            (self.rect_x - width, self.rect_y + triangle_height+height),### TOP LEFT VERT
            (self.rect_x - width, self.rect_y + triangle_height), ### BOTTOM LEFT VERT
            (self.rect_x + width, self.rect_y + triangle_height), ### BOTTOM RIGHT VERT
            (self.rect_x + width, self.rect_y + triangle_height+height), ### TOP RIGHT VERT

            # Triangle vertices
            (self.rect_x - triangle_half_width, self.rect_y + triangle_height), ### Top left
            (self.rect_x + triangle_half_width, self.rect_y + triangle_height), ### Top Right
            (self.rect_x, self.rect_y) ### Bottom vert
        )
        main_batch = batch_for_shader(shader, 'TRIS', {"pos": main_vertices}, indices=indices)

        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        shader.bind()
        shader.uniform_float("color", self.note_color)  # RGBA black color
        main_batch.draw(shader)
        bgl.glDisable(bgl.GL_BLEND)

        # Draw the note text
        blf.position(font_id, text_position_x, self.rect_y + triangle_height + height / 3, 0)
        blf.color(font_id, 1, 1, 1, 1)  # RGBA: white color
        blf.draw(font_id, self.note)


    def modal(self, context, event):
        context.area.tag_redraw()

        nodeshelf_props = bpy.context.scene.nodeshelf_props
        show_notes = nodeshelf_props.show_notes
        if show_notes == "Show Notes": ### don't add notes if notes are set to hidden, this is useless bcus operator only shows up when notes are enabled, but just in case
            if event.type == 'MOUSEMOVE' and not self.fixed:
                # Update the rectangle position, this is the XY where the mouse starts drawing
                self.rect_x, self.rect_y = event.mouse_region_x, event.mouse_region_y

                # Get nodes from active tree
                self.tree = context.space_data.node_tree
                nodes = self.tree.nodes

                # Convert mouse coordinates to node view coordinates
                self.mx, self.my = bpy.context.region.view2d.region_to_view(event.mouse_region_x, event.mouse_region_y)
                # Check if mouse is hovering over any node
                for node in nodes:
                    if node.location.x <= self.mx <= (node.location.x + node.width) and \
                            node.location.y - node.height <= self.my <= (node.location.y):
                        # Snap the x,y to the top center of the node
                        self.mx, self.my = node.location.x + node.width / 2, node.location.y
                        self.is_linked = True
                        self.linked_node = node.name
                        break
                else:
                    self.is_linked = False
                    self.linked_node = None


            elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                self.fixed = True
                # Convert the fixed coordinates to the view space

                print(f"region when add leftmouse is pressed: {context.region.type}")
                self.rect_x, self.rect_y = bpy.context.region.view2d.region_to_view(self.mx, self.my)

                ###at this point a note is added with a shape and text
                # Create widget
                unique_id = str(time.time())
                widget = NoteWidget(unique_id, str(self.note), (self.note_color[0], self.note_color[1],self.note_color[2],self.note_color[3]), [self.mx, self.my], self.is_linked, self.linked_node)
                notesFolder = os.path.join(self.data_folder, f"NotesFolder")
                os.makedirs(notesFolder, exist_ok=True)
                js = os.path.join(notesFolder, f"{self.tree.name}_Notes.json")
                with open(js, 'a') as f:
                    json.dump(widget.serialize(), f)
                    f.write('\n')

                self.unregister_handlers()
                return {"FINISHED"}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):

        if context.area.type == 'NODE_EDITOR':
            args = (self, context)
            self.register_handlers(context, args)

            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Node editor not active, could not run operator")
            return {'CANCELLED'}

    def register_handlers(self, context, args):
        self._handle = bpy.types.SpaceNodeEditor.draw_handler_add(self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)

    def unregister_handlers(self):
        bpy.app.driver_namespace['note_alert'] = True ### alert the notes manager about a new note
        bpy.types.SpaceNodeEditor.draw_handler_remove(self._handle, 'WINDOW')


class NODESHELF_OT_manage_notes(bpy.types.Operator):
    bl_idname = "nodeshelf.manage_notes"
    bl_label = "Manage Notes"
    base_zoom_level: bpy.props.FloatProperty()


    def __init__(self):
        self.rect_x = 0
        self.rect_y = 0
        self.fixed = False
        nodeshelf_props = bpy.context.scene.nodeshelf_props
        ns_prefs = bpy.context.preferences.addons['NodeShelf'].preferences
        self.data_folder = ns_prefs.data_folder
        self.notes = []  # List to store notes from json
        self.selected_notes = []
        self.note_color = nodeshelf_props.note_color
        self.base_font_size = ns_prefs.font_size
        self.border_color = ns_prefs.border_color
        self.alignment = ns_prefs.alignment
        self.active_note = None
        self.dragging = False
        self.is_selecting = False
        self.is_linked = False
        self.linked_node = None


    def draw_callback_px(self, context, args):
        region = bpy.context.region
        nodeshelf_props = bpy.context.scene.nodeshelf_props
        ns_prefs = bpy.context.preferences.addons['NodeShelf'].preferences
        th = 1
        borderColor = (self.border_color[0], self.border_color[1], self.border_color[2], self.note_color[3])
        self.tree = bpy.context.space_data.node_tree
        nodes = self.tree.nodes
        show_notes = nodeshelf_props.show_notes
        if show_notes == "Show Notes": ### don't draw to screen if notes are hidden
            for note in self.notes:
                # Retrieve note data from note dictionary
                self.note = note['note']
                self.note_color = tuple(note['color'])
                self.mx, self.my = note['coordinates']
                if note['is_linked'] == True:
                    l_n = nodes[note['linked_node']]
                    if ns_prefs.alignment == "CENTER":
                        off_x = l_n.width/2
                    if ns_prefs.alignment == "LEFT":
                        off_x = 0
                    if ns_prefs.alignment == "RIGHT":
                        off_x = l_n.width

                    self.mx = l_n.location[0]+off_x
                    self.my = l_n.location[1]+5

                # Calculate the size of one pixel in view coordinates
                px_x, px_y = region.view2d.region_to_view(1, 1)
                zero_x, zero_y = region.view2d.region_to_view(0, 0)
                pixel_size_x = px_x - zero_x
                pixel_size_y = px_y - zero_y

                # Scale font size from base zoom level (getting proportions of zoom)
                font_size = self.base_font_size / pixel_size_x * 0.75
                # Draw the note text
                font_id = 0  # default Blender font

                # Set the font size before getting dimensions
                blf.size(font_id, int(font_size), 72)  # font size

                # Calculate the length of the note text
                text_width_pixel, _ = blf.dimensions(font_id, self.note)
                text_width_view = text_width_pixel / pixel_size_x  # Convert to view coordinates

                # Calculate rectangle and triangle dimensions
                width = (text_width_pixel+15)/2   # Use text width as rectangle width
                height = 20 / pixel_size_y
                triangle_height = 10 / pixel_size_y
                triangle_half_width = 10 / pixel_size_x

                # Convert view space coordinates back to region space for drawing

                self.rect_x, self.rect_y = region.view2d.view_to_region(self.mx, self.my)

                # Adjust text position for centered alignment
                text_position_x = self.rect_x - text_width_pixel / 2

                # Draw larger shapes (to serve as borders)
                border_vertices = (
                    (self.rect_x - width - th, self.rect_y + triangle_height+height + th), ### TOP LEFT VERT
                    (self.rect_x - width - th, self.rect_y + triangle_height - th), ### BOTTOM LEFT VERT
                    (self.rect_x + width + th, self.rect_y + triangle_height - th), ### BOTTOM RIGHT VERT
                    (self.rect_x + width + th, self.rect_y + triangle_height+height + th), ### TOP RIGHT VERT

                    # Triangle vertices
                    (self.rect_x - triangle_half_width - th, self.rect_y + triangle_height + th), ### Top left
                    (self.rect_x + triangle_half_width + th*2, self.rect_y + triangle_height + th), ### Top Right
                    (self.rect_x, self.rect_y - th) ### Bottom vert
                )
                indices = ((0, 1, 2), (2, 3, 0), (4, 5, 6))
                # Draw border (Each note will have its own shader because color may differ)
                border_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
                border_batch = batch_for_shader(border_shader, 'TRIS', {"pos": border_vertices}, indices=indices)
                border_shader.bind()
                bgl.glEnable(bgl.GL_BLEND)
                bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
                border_shader.uniform_float("color", borderColor)  # RGBA white color
                border_batch.draw(border_shader)
                bgl.glDisable(bgl.GL_BLEND)

                # Draw main shapes
                main_vertices = (
                    (self.rect_x - width, self.rect_y + triangle_height+height),### TOP LEFT VERT
                    (self.rect_x - width, self.rect_y + triangle_height), ### BOTTOM LEFT VERT
                    (self.rect_x + width, self.rect_y + triangle_height), ### BOTTOM RIGHT VERT
                    (self.rect_x + width, self.rect_y + triangle_height+height), ### TOP RIGHT VERT

                    # Triangle vertices
                    (self.rect_x - triangle_half_width, self.rect_y + triangle_height), ### Top left
                    (self.rect_x + triangle_half_width, self.rect_y + triangle_height), ### Top Right
                    (self.rect_x, self.rect_y) ### Bottom vert
                )
                main_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
                main_batch = batch_for_shader(main_shader, 'TRIS', {"pos": main_vertices}, indices=indices)
                main_shader.bind()
                bgl.glEnable(bgl.GL_BLEND)
                bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
                main_shader.uniform_float("color", self.note_color)  # RGBA black color
                main_batch.draw(main_shader)
                bgl.glDisable(bgl.GL_BLEND)

                if note == self.active_note:
                    thi = 5
                    underlineColor = (0.2, 1.0, 0.3, 1.0)
                elif note in self.selected_notes:
                    thi = 3
                    underlineColor = (1.0, 0.4, 0.3, 1.0)
                else:
                    thi = 1
                    underlineColor = (1.0, 1.0, 1.0, 1.0)


                if (self.active_note is not None):
                    if note['id'] == self.active_note['id'] or any((s_n is not None) and (note['id'] == s_n['id']) for s_n in self.selected_notes):
                        # Draw line on top of the rectangle for active and selected notes
                        line_vertices = [(self.rect_x - width, self.rect_y + triangle_height + height + 10 / pixel_size_y), # Start point of line, 2px above the rectangle
                                         (self.rect_x + width, self.rect_y + triangle_height + height + 10 / pixel_size_y)]  # End point of line, 2px above the rectangle

                        line_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
                        line_batch = batch_for_shader(line_shader, 'LINES', {"pos": line_vertices})
                        line_shader.bind()
                        bgl.glLineWidth(thi)  # Set line thickness to thi pixels
                        line_shader.uniform_float("color", underlineColor)  # RGBA underline color
                        line_batch.draw(line_shader)
                        line_batch.draw(line_shader)


                # Draw the note text
                blf.position(font_id, text_position_x, self.rect_y + triangle_height + height / 3, 0)
                blf.color(font_id, 1, 1, 1, 1)  # RGBA: white color
                blf.draw(font_id, self.note)

    def modal(self, context, event):

        area = bpy.context.area
        region = self.get_region(area, 'WINDOW')
        context.area.tag_redraw()
        self.tree = context.space_data.node_tree
        nodes = self.tree.nodes
        nodeshelf_props = context.scene.nodeshelf_props
        show_notes = nodeshelf_props.show_notes
        dns = bpy.app.driver_namespace


        if not dns.get('initialized'): # only way to turn off modal operator
            self.unregister_handlers()
            return {'FINISHED'}
        if show_notes == "Show Notes": ### don't do anything if notes are hidden
            if dns.get('note_alert'):
                self.read_draw(context)
                dns['note_alert'] = False


            if event.type == 'LEFTMOUSE' and event.value == 'PRESS' and not self.dragging:
                self.read_draw(context)
                self.mouse_x, self.mouse_y = event.mouse_region_x, event.mouse_region_y
                closest_note = None
                closest_distance = 20  # The threshold distance
                for note in self.notes:
                    mx, my = note['coordinates']
                    screen_x, screen_y = bpy.context.region.view2d.view_to_region(mx, my)

                    distance = ((screen_x - self.mouse_x) ** 2 + (screen_y - self.mouse_y) ** 2) ** 0.5 #local distance
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_note = note
                        print(f"note is {closest_note}")
                if closest_note is None: ### click anywhere else
                    self.dragging = False
                else:
                    self.dragging = True
                    if self.is_selecting:
                        if self.active_note not in self.selected_notes:
                            self.selected_notes.append(self.active_note)#appending previous if selecting
                    self.active_note = closest_note
                    if self.active_note['is_linked']:
                        self.active_note['is_linked'] = False
                        self.active_note['linked_node'] = None
                    return {'RUNNING_MODAL'}

            if event.type == 'MOUSEMOVE' and self.dragging:
                self.mouse_x, self.mouse_y = event.mouse_region_x, event.mouse_region_y ## new coordinates after moving the mouse
                region_x, region_y = region.view2d.region_to_view(self.mouse_x, self.mouse_y) ## new local coordinates

                # Check if mouse is hovering over any node
                for node in nodes:
                    if node.location.x <= region_x <= (node.location.x + node.width) and \
                            node.location.y - node.height <= region_y <= (node.location.y):
                        # Snap the x,y to the top center of the node
                        region_x, region_y = node.location.x + node.width / 2, node.location.y
                        self.is_linked = True
                        self.linked_node = node.name
                        for n in nodes:
                            n.select = False
                        node.select = True
                        nodes.active = node
                        break
                else:
                    self.is_linked = False
                    self.linked_node = None

                self.active_note['coordinates'] = (region_x, region_y)
                self.active_note['is_linked'] = self.is_linked
                self.active_note['linked_node'] = self.linked_node

                self.update_json_file()  # Assuming this function writes the notes back into the JSON file
                self.read_draw(context)
                return {'RUNNING_MODAL'}

            elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self.dragging:
                self.dragging = False

            elif event.type == 'ESC':
                self.selected_notes = []
                self.active_note = None
                dns["active_note"] = None
                dns["selected_notes"] = []

            if event.type == 'LEFT_SHIFT' and event.value=="PRESS":
                self.is_selecting=True

            if event.type == 'LEFT_SHIFT' and event.value=="RELEASE":
                self.is_selecting=False

            if self.active_note:
                dns["active_note"] = self.active_note

            if self.selected_notes:
                dns["selected_notes"] = self.selected_notes


        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type == 'NODE_EDITOR':
            args = (self, context)
            bpy.app.driver_namespace["notes_manager_on"] = True
            self.read_draw(context) ### gets us the self.notes

            self.register_handlers(context, args)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Node editor not active, could not run operator")
            return {'CANCELLED'}

    def update_json_file(self):
        nodes = self.tree.nodes
        notesFolder = os.path.join(self.data_folder, f"NotesFolder")
        js = os.path.join(notesFolder, f"{self.tree.name}_Notes.json")
        if not os.path.exists(js):
            print("No Json Found")
            return {'CANCELLED'}
        with open(js, 'r') as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            note = json.loads(line)
            if note['id'] == self.active_note['id']:
                if self.active_note['is_linked']: ### change location of certain notes periodically if they are linked to a node because node movement is not trackable in this modal
                    linked_node = nodes.get(self.active_note['linked_node'])
                    if linked_node:
                        self.active_note['coordinates'] = tuple(linked_node.location)

                lines[i] = json.dumps(self.active_note) + "\n"  # Update the note line

        with open(js, 'w') as f:
            f.writelines(lines)  # Write the updated lines back to the file

    def periodic_update(self):
        ns_prefs = bpy.context.preferences.addons['NodeShelf'].preferences
        nodes = self.tree.nodes
        notesFolder = os.path.join(self.data_folder, "NotesFolder")
        os.makedirs(notesFolder, exist_ok=True)  # Make sure the directory exists
        js = os.path.join(notesFolder, f"{self.tree.name}_Notes.json")

        # Now we are sure the file exists, we can load it
        with open(js, 'r') as f:
            lines = f.readlines()
            notes = [json.loads(line) for line in lines if line.strip() != '[]']

        updated_notes = []
        linked_notes = []
        # Go through all notes
        if notes !=[]:
            for note in notes:
                if note['is_linked']:
                    linked_notes.append(note['id'])
                    node = nodes.get(note['linked_node'])
                    if node:
                        if ns_prefs.alignment == "CENTER":
                            off_x = node.width / 2
                        if ns_prefs.alignment == "LEFT":
                            off_x = 0
                        if ns_prefs.alignment == "RIGHT":
                            off_x = node.width

                        el_x = node.location[0] + off_x
                        el_y = node.location[1] + 5
                        note['coordinates'] = (el_x, el_y)
                updated_notes.append(note)

        # Write all notes back to file
        with open(js, 'w') as f:
            for note in updated_notes:
                f.write(json.dumps(note))
                f.write('\n')

        return 1.0

    def read_draw(self, context):
        # Load all notes from the JSON file
        self.notes = []
        notesFolder = os.path.join(self.data_folder, f"NotesFolder")
        js = os.path.join(notesFolder, f"{bpy.context.space_data.node_tree.name}_Notes.json")
        # Check if file exists, if not create it with an empty array
        if not os.path.isfile(js):
            with open(js, 'w') as f:
                json.dump([], f)
        with open(js, 'r') as f:
            for line in f:
                note = json.loads(line)  # Load JSON from line
                if note:  # If the note is not empty
                    self.notes.append(note)  # Add it to the list

    def get_region(self, area, region_type):
        for region in area.regions:
            if region.type == region_type:
                return region
        return None

    def register_handlers(self, context, args):
        self._handle = bpy.types.SpaceNodeEditor.draw_handler_add(self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)

        for area in bpy.context.screen.areas:
            if area.type == 'NODE_EDITOR':
                self.tree = area.spaces.active.node_tree
                break
        bpy.app.timers.register(self.periodic_update)

    def unregister_handlers(self):
        bpy.types.SpaceNodeEditor.draw_handler_remove(self._handle, 'WINDOW')



