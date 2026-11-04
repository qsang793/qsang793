"""Renders Subaru's frames for the City: the VRM model posed by Mixamo animations, seen at the City's angle.

Usage: blender -b --python scripts/render_subaru.py -- MODEL.vrm MIXAMO_DIR OUT_DIR [sheet]
MIXAMO_DIR holds run.fbx, jump.fbx, fall.fbx and idle.fbx, exported "Without Skin" at 30 fps.
Neither the model nor the animations are kept in the repo (docs/adr/0003); only the frames are.
"""
import json, math, os, sys
import bpy, addon_utils
from mathutils import Matrix, Vector

MODEL, MIXAMO, OUT = sys.argv[sys.argv.index("--") + 1:][:3]
SHEET = "sheet" in sys.argv
# (name, animation, frame): the frames the City uses. Picked from a contact sheet (`sheet`).
FRAMES = [("run0", "run", 7), ("run1", "run", 11), ("run2", "run", 16), ("jump", "jump", 16), ("fall", "fall", 10), ("stand", "idle", 1)]
# VRM 0 humanoid bone -> Mixamo bone. Rotations are copied as world-space deltas from each rest pose, so chains of
# different length (Mixamo's three spine bones, VRM's two) still line up.
MAP = {
    "hips": "Hips", "spine": "Spine", "chest": "Spine2", "neck": "Neck", "head": "Head",
    **{f"{s}{v}": f"{S}{m}" for s, S in (("left", "Left"), ("right", "Right")) for v, m in (
        ("Shoulder", "Shoulder"), ("UpperArm", "Arm"), ("LowerArm", "ForeArm"), ("Hand", "Hand"),
        ("UpperLeg", "UpLeg"), ("LowerLeg", "Leg"), ("Foot", "Foot"), ("Toes", "ToeBase"))},
}
PX = 192  # square render; Subaru is drawn 40 units tall, so this is about 2x for retina


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("bl_ext.user_default.vrm", default_set=True)
    bpy.ops.import_scene.vrm(filepath=MODEL)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    arm.rotation_mode = "XYZ"  # the VRM import uses quaternions, which would ignore rotation_euler
    human = {b.bone: b.node.bone_name for b in arm.data.vrm_addon_extension.vrm0.humanoid.human_bones}
    pairs = [(human[v], "mixamorig:" + m) for v, m in MAP.items() if human.get(v)]
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = PX
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    # No Freestyle: it darkens MToon to a silhouette. The City draws the outline itself, in the theme's color.
    # MToon is a toon shader: a white world and one light from the camera's side give flat, anime-bright colors.
    world = bpy.data.worlds.new("w"); sc.world = world
    world.color = (1, 1, 1)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4
    sc.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 3.2
    sc.collection.objects.link(cam); sc.camera = cam
    aim(cam, sc)
    sun.rotation_euler = cam.rotation_euler.copy()
    sun.rotation_euler.z += math.radians(-25)  # a little from the left, so the face keeps a shadow side
    return arm, pairs, cam


def aim(cam, sc):
    """Turns the camera until the world axes fall where the City draws them.

    Subaru runs along +X, which must point like a City week (15, 2.2: right, a little down); -Y must point like a
    weekday (-6, 6: down and to the left, toward the viewer); up stays up. Pitch and yaw are searched, not derived.
    """
    from bpy_extras.object_utils import world_to_camera_view as w2c
    want = [Vector((15, -2.2)).normalized(), Vector((-6, -6)).normalized()]  # screen y up
    best = None
    for pitch in range(5, 60):
        for yaw in range(0, 360, 1):
            cam.rotation_euler = (math.radians(90 - pitch), 0, math.radians(yaw))
            cam.location = cam.rotation_euler.to_matrix() @ Vector((0, 0, 10)) + Vector((0, 0, .9))
            bpy.context.view_layer.update()
            o = w2c(sc, cam, Vector((0, 0, 0)))
            got = [(w2c(sc, cam, a) - o).to_2d().normalized() for a in (Vector((1, 0, 0)), Vector((0, -1, 0)))]
            err = sum((g - w).length for g, w in zip(got, want))
            if best is None or err < best[0]:
                best = (err, pitch, yaw)
    _, pitch, yaw = best
    cam.rotation_euler = (math.radians(90 - pitch), 0, math.radians(yaw))
    cam.location = cam.rotation_euler.to_matrix() @ Vector((0, 0, 10)) + Vector((0, 0, .9))
    bpy.context.view_layer.update()
    print("camera pitch", pitch, "yaw", yaw)


def load(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(MIXAMO, name + ".fbx"))
    new = set(bpy.data.objects) - before
    for o in new:
        o.hide_render = True
    return next(o for o in new if o.type == "ARMATURE")


def retarget(arm, src, pairs, frame):
    bpy.context.scene.frame_set(frame)
    arm.rotation_euler = (0, 0, 0)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.context.view_layer.update()
    tw = arm.matrix_world.to_quaternion()
    # Parents first, so each child's world rotation is set against its parent's new pose.
    order = sorted(pairs, key=lambda p: len(arm.pose.bones[p[0]].parent_recursive))
    for t, s in order:
        sp, tp = src.pose.bones[s], arm.pose.bones[t]
        rest_s = (src.matrix_world @ sp.bone.matrix_local).to_quaternion()
        pose_s = (src.matrix_world @ sp.matrix).to_quaternion()
        rest_t = tw @ tp.bone.matrix_local.to_quaternion()
        want = tw.inverted() @ (pose_s @ rest_s.inverted()) @ rest_t
        m = want.to_matrix().to_4x4()
        m.translation = tp.matrix.translation
        tp.matrix = m
        bpy.context.view_layer.update()
    # Running along +X, the way the City's weeks run; the model faces -Y at rest.
    arm.rotation_euler = (0, 0, math.radians(90))
    bpy.context.view_layer.update()


def main():
    arm, pairs, cam = setup()
    sc = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    srcs = {n: load(n) for n in ("run", "jump", "fall", "idle")}
    if SHEET:
        jobs = [(f"{n}-{f:02d}", n, f) for n, src in srcs.items()
                for f in range(1, int(src.animation_data.action.frame_range[1]) + 1, 3)]
    else:
        jobs = FRAMES
    for name, anim, frame in jobs:
        retarget(arm, srcs[anim], pairs, frame)
        sc.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
    if not SHEET:
        crop(jobs, cam)


def crop(jobs, cam):
    """Cuts every frame to one shared box and saves it as WebP, so the ground point sits at the same pixel in all."""
    import numpy as np
    from bpy_extras.object_utils import world_to_camera_view as w2c
    imgs = {n: bpy.data.images.load(os.path.join(OUT, n + ".png")) for n, *_ in jobs}
    # Blender stores pixels bottom-up; flip so row 0 is the top, like the SVG.
    px = {n: np.array(i.pixels[:]).reshape(PX, PX, 4)[::-1] for n, i in imgs.items()}
    ys, xs = np.nonzero(np.any([p[..., 3] > .02 for p in px.values()], axis=0))
    x0, x1, y0, y1 = xs.min() - 2, xs.max() + 3, ys.min() - 2, ys.max() + 3
    for n, p in px.items():
        c = p[y0:y1, x0:x1][::-1]
        out = bpy.data.images.new(n, x1 - x0, y1 - y0, alpha=True)
        out.pixels = c.ravel()
        out.filepath_raw = os.path.join(OUT, n + ".webp")
        out.file_format = "WEBP"
        out.save(quality=82)
        os.remove(os.path.join(OUT, n + ".png"))
    # Where the ground under Subaru's hips lands, so the City can stand him on a rooftop.
    p = w2c(bpy.context.scene, cam, Vector((0, 0, 0)))
    json.dump({"size": [int(x1 - x0), int(y1 - y0)], "ground": [round(p.x * PX - x0, 1), round((1 - p.y) * PX - y0, 1)],
               "px_per_m": round(PX / cam.data.ortho_scale, 2)}, open(os.path.join(OUT, "frames.json"), "w"))


main()
