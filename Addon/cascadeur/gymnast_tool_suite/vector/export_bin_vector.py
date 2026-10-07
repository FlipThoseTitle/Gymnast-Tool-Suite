# original script by Sonamenil

import csc
import math
import os
import struct
import tempfile
from pathlib import Path


NODE_ORDER = [
    "thigh_1",
    "thigh_2",
    "stomach",
    "chest",
    "neck",
    "arm_1",
    "arm_2",
    "calf_1",
    "calf_2",
    "foot_1",
    "foot_2",
    "toes_1",
    "Heel_1_end",
    "toes_1_end",
    "ToeS_1_end",
    "Heel_2_end",
    "toes_2",
    "toes_2_end",
    "ToeS_2_end",
    "forearm_1",
    "forearm_2",
    "hand_1",
    "hand_2",
    "fingers_1",
    "fingers_1_end",
    "KnucklesS_1_end",
    "fingers_2",
    "fingers_2_end",
    "KnucklesS_2_end",
    "head",
    "HeadF",
    "ChestS_1_end",
    "ChestS_2_end",
    "StomachS_1_end",
    "StomachS_2_end",
    "ChestF_end",
    "StomachF_end",
    "PelvisF_end",
    "HeadS_1_end",
    "HeadS_2_end",
    "HeadF_end",
    "pelvis",
    "DetectorH",
    "DetectorV",
    "COM_end",
    "Camera",
]


READ_ERRORS = (
    RuntimeError,
    TypeError,
    ValueError,
    IndexError,
    OverflowError,
)


def command_name():
    return "Gymnast Tool Suite.Vector.Export Animation"


def get_nodes(model_viewer, behaviour_viewer):
    nodes = []

    for name in NODE_ORDER:
        objects = model_viewer.get_objects(name)

        if len(objects) != 1:
            raise RuntimeError(
                f"Expected exactly one required node: {name}; "
                f"found {len(objects)}"
            )

        transform = behaviour_viewer.get_behaviour_by_name(
            objects[0],
            "Transform"
        )

        if transform is None or transform.is_null():
            raise RuntimeError(f"No Transform found for: {name}")

        position = behaviour_viewer.get_behaviour_data(
            transform,
            "global_position"
        )

        if position is None or position.is_null():
            raise RuntimeError(f"No global_position found for: {name}")

        nodes.append((name, position))

    return nodes


def find_last_frame(data_viewer, nodes, start_frame, end_frame):
    frame = end_frame

    while frame >= start_frame:
        try:
            for _, position_id in nodes:
                data_viewer.get_data_value(position_id, frame)

            return frame

        except READ_ERRORS:
            frame -= 1

    raise RuntimeError(
        f"No common readable frame range for required nodes: "
        f"{start_frame}..{end_frame}"
    )


def get_position(data_viewer, position_id, node_name, frame):
    try:
        value = data_viewer.get_data_value(position_id, frame)

        xyz = tuple(float(value[i]) for i in range(3))

        if not all(math.isfinite(v) for v in xyz):
            raise ValueError("position contains a non-finite coordinate")

        return xyz

    except (
        RuntimeError,
        TypeError,
        ValueError,
        IndexError,
        OverflowError,
        struct.error,
    ) as exc:
        raise RuntimeError(
            f"Cannot export node {node_name} at frame {frame}: {exc}"
        ) from exc


def build_binary(data_viewer, nodes, start_frame, end_frame):
    frame_count = end_frame - start_frame + 1

    binary = bytearray(struct.pack("<i", frame_count))

    for frame in range(start_frame, end_frame + 1):
        block = bytearray(
            struct.pack(
                "<Bi",
                0,
                len(NODE_ORDER)
            )
        )

        for node_name, position_id in nodes:
            position = get_position(
                data_viewer,
                position_id,
                node_name,
                frame
            )

            block.extend(
                struct.pack(
                    "<fff",
                    *position
                )
            )

        binary.extend(block)

        print(
            f"Frame {frame}: exported {len(NODE_ORDER)} nodes"
        )

    return binary


def save_binary(filepath, binary):
    if not filepath:
        return

    output_path = Path(filepath)

    if output_path.suffix.lower() != ".bin":
        if output_path.suffix:
            output_path = output_path.with_suffix(".bin")
        else:
            output_path = Path(str(output_path) + ".bin")

    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output_path.parent,
            prefix=output_path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)

            file.write(binary)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary, output_path)
        temporary = None

        print(f"Saved: {output_path}")

    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(scene):
    app = csc.app.get_application()

    scene_view = app.current_scene()

    if scene_view is None:
        raise RuntimeError("No active scene to export")

    domain_scene = scene_view.domain_scene()
    model_viewer = domain_scene.model_viewer()
    behaviour_viewer = model_viewer.behaviour_viewer()
    data_viewer = model_viewer.data_viewer()

    boundary = scene_view.animation_boundary()
    start_frame = boundary.first_frame
    end_frame = boundary.last_frame

    if end_frame < start_frame:
        raise RuntimeError("Animation boundary is empty")

    nodes = get_nodes(
        model_viewer,
        behaviour_viewer
    )

    export_end_frame = find_last_frame(
        data_viewer,
        nodes,
        start_frame,
        end_frame
    )

    if export_end_frame != end_frame:
        print(
            f"Animation boundary ends at frame {end_frame}, "
            f"but at least one node has no data there. "
            f"Exporting through frame {export_end_frame}."
        )

    binary = build_binary(
        data_viewer,
        nodes,
        start_frame,
        export_end_frame
    )

    def save(filepath):
        save_binary(filepath, binary)

    app.get_file_dialog_manager().show_save_file_dialog(
        "Save animation as",
        "",
        ["*.bin"],
        save
    )