"""Renders Subaru's frames for the City: the VRM model posed by Mixamo animations, seen at the City's angle.

Usage: blender -b --python scripts/render_subaru.py -- MODEL.vrm MIXAMO_DIR OUT_DIR [sheet]
MIXAMO_DIR holds run.fbx (Running), hop.fbx (Jumping Forward), jump.fbx (Standing Jump Running), fall.fbx and idle.fbx,
exported "Without Skin" at 30 fps. The frames come out as one strip, subaru.webp, described by frames.json.
Neither the model nor the animations are kept in the repo (docs/adr/0003); only the frames are.
"""
import json, math, os, sys
import bpy, addon_utils
from mathutils import Matrix, Vector

MODEL, MIXAMO, OUT = sys.argv[sys.argv.index("--") + 1:][:3]
SHEET = "sheet" in sys.argv
CLIPS = ("run", "hop", "jump", "fall", "idle")
# (name, animation, frame), in strip order. Phases read off the clips' hip and toe heights: run is a 22-frame cycle.
# hop crouches to its lowest at 20, pushes up through 24 with its feet still down, flies 25-36, touches down at 37
# and is lowest again at 41. jump leaves the ground at 24 and ends in the air.
HOP = dict(crouch=(10, 15, 20), push=(22, 24), air=(26, 29, 32, 35), land=(37, 39, 41), recover=(46, 54))
FRAMES = ([(f"run{i}", "run", 1 + 2 * i) for i in range(11)]
          + [(f"{phase}{i}", "hop", f) for phase, fs in HOP.items() for i, f in enumerate(fs)]
          + [(f"leap{i}", "jump", f) for i, f in enumerate((24, 27, 30, 33))]
          + [("fall", "fall", 10), ("stand", "idle", 1)])
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
    arm.location = (0, 0, 0)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.context.view_layer.update()
    tw = arm.matrix_world.to_quaternion()
    vrm = {s: t for t, s in pairs}
    toes = [vrm["mixamorig:LeftToeBase"], vrm["mixamorig:RightToeBase"]]
    low = lambda o, bones: min((o.matrix_world @ o.pose.bones[b].head).z for b in bones)
    hips_rest, toes_rest = (arm.matrix_world @ arm.pose.bones[vrm["mixamorig:Hips"]].head).z, low(arm, toes)
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
    # Only rotations carry over, so the hips would stay at standing height and a crouch would lift the feet.
    # With a foot down, the lowest toe goes back on the ground; in the air, the hips follow the clip's, scaled to Subaru.
    if low(src, ["mixamorig:LeftToeBase", "mixamorig:RightToeBase"]) < .02:
        arm.location.z = toes_rest - low(arm, toes)
    else:
        hips = src.pose.bones["mixamorig:Hips"]
        arm.location.z = hips_rest * ((src.matrix_world @ hips.head).z / (src.matrix_world @ hips.bone.head_local).z - 1)
    # Running along +X, the way the City's weeks run; the model faces -Y at rest.
    arm.rotation_euler = (0, 0, math.radians(90))
    bpy.context.view_layer.update()


def main():
    arm, pairs, cam = setup()
    sc = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    srcs = {n: load(n) for n in CLIPS}
    if SHEET:
        jobs = [(f"{n}-{f:02d}", n, f) for n, src in srcs.items()
                for f in range(1, int(src.animation_data.action.frame_range[1]) + 1, 3)]
    else:
        jobs = FRAMES
    feet = {n: {} if n == "run" else anchors(arm, src, pairs) for n, src in srcs.items()}
    for name, anim, frame in jobs:
        retarget(arm, srcs[anim], pairs, frame)
        # Stand him on his feet, not his hips, so a crouch or a landing puts his feet on the middle of the roof.
        # The run keeps the hips: its planted foot slides back at the running speed instead.
        arm.location.xy = [-v for v in feet[anim].get(frame, (0, 0))]
        bpy.context.view_layer.update()
        sc.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
    if not SHEET:
        crop(jobs, cam, run_speed(arm, srcs["run"], pairs, cam))


def anchors(arm, src, pairs):
    """Where the planted feet are in each frame of a clip, relative to the hips; in the air, slid evenly between the
    last takeoff and the next landing, so the body carries on smoothly from one to the other."""
    vrm = {s: t for t, s in pairs}
    first, last = (int(f) for f in src.animation_data.action.frame_range)
    down = {}
    for f in range(first, last + 1):
        retarget(arm, src, pairs, f)
        planted = [vrm[f"mixamorig:{side}{b}"] for side in ("Left", "Right") for b in ("Foot", "ToeBase")
                   if (src.matrix_world @ src.pose.bones[f"mixamorig:{side}ToeBase"].head).z < .02]
        if planted:
            down[f] = sum(((arm.matrix_world @ arm.pose.bones[b].head).xy for b in planted), Vector((0, 0))) / len(planted)
    keys = sorted(down)
    if not keys:
        return {}
    out = {}
    for f in range(first, last + 1):
        a = max((k for k in keys if k <= f), default=keys[0])
        b = min((k for k in keys if k >= f), default=keys[-1])
        out[f] = tuple(down[a].lerp(down[b], (f - a) / (b - a)) if b != a else down[a])
    return out


def run_speed(arm, src, pairs, cam):
    """How fast the planted foot slides back in the run cycle, in render px/s: the speed Subaru must run not to skate."""
    from bpy_extras.object_utils import world_to_camera_view as w2c
    vrm = {s: t for t, s in pairs}
    feet, moves = [], []
    for f in range(1, 23):
        retarget(arm, src, pairs, f)
        feet.append([(w2c(bpy.context.scene, cam, arm.matrix_world @ arm.pose.bones[vrm[b]].head).x * PX,
                      (src.matrix_world @ src.pose.bones[b].head).z < .02)
                     for b in ("mixamorig:LeftToeBase", "mixamorig:RightToeBase")])
    for a, b in zip(feet, feet[1:]):
        moves += [x0 - x1 for (x0, down0), (x1, down1) in zip(a, b) if down0 and down1]
    return 30 * sum(moves) / len(moves)


def crop(jobs, cam, speed):
    """Cuts every frame to one shared box and lays them side by side in one WebP strip, in FRAMES order,
    so the ground point sits at the same pixel in every frame."""
    import numpy as np
    from bpy_extras.object_utils import world_to_camera_view as w2c
    imgs = {n: bpy.data.images.load(os.path.join(OUT, n + ".png")) for n, *_ in jobs}
    # Blender stores pixels bottom-up; flip so row 0 is the top, like the SVG.
    px = {n: np.array(i.pixels[:]).reshape(PX, PX, 4)[::-1] for n, i in imgs.items()}
    ys, xs = np.nonzero(np.any([p[..., 3] > .02 for p in px.values()], axis=0))
    x0, x1, y0, y1 = xs.min() - 2, xs.max() + 3, ys.min() - 2, ys.max() + 3
    strip = np.concatenate([px[n][y0:y1, x0:x1] for n, *_ in jobs], axis=1)[::-1]
    out = bpy.data.images.new("subaru", strip.shape[1], strip.shape[0], alpha=True)
    out.pixels = strip.ravel()
    out.filepath_raw = os.path.join(OUT, "subaru.webp")
    out.file_format = "WEBP"
    out.save(quality=82)
    for n, *_ in jobs:
        os.remove(os.path.join(OUT, n + ".png"))
    # The ground point is the middle of his feet on the floor, which the City puts on the middle of a roof. anchors()
    # centres the ankle and toe joints on the world origin, but a foot runs from heel to toe tip, so slide the origin
    # back along the way he faces (+X) until it sits under the middle of his standing soles. (The soles' lowest pixel
    # would not do: it is the part of the foot nearest the viewer.)
    scr = lambda v: Vector((w2c(bpy.context.scene, cam, v).x * PX - x0, (1 - w2c(bpy.context.scene, cam, v).y) * PX - y0))
    o, face = scr(Vector((0, 0, 0))), scr(Vector((1, 0, 0))) - scr(Vector((0, 0, 0)))
    soles = px["stand"][y0:y1, x0:x1, 3] > .3
    bottom = int(np.nonzero(soles.any(axis=1))[0].max())
    g = o + face * ((float(np.nonzero(soles[bottom - 5:bottom + 1].any(axis=0))[0].mean()) - o.x) / face.x)
    json.dump({"size": [int(x1 - x0), int(y1 - y0)], "ground": [round(g.x, 1), round(g.y, 1)],
               "px_per_m": round(PX / cam.data.ortho_scale, 2), "run_px_s": round(speed, 1),
               "frames": [n for n, *_ in jobs]}, open(os.path.join(OUT, "frames.json"), "w"))


main()
