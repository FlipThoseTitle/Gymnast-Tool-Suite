import math
from pathlib import Path

import csc
import numpy as np

ROTATION_HELPERS = frozenset({
    'HeadF', 'ChestS_1_end', 'ChestS_2_end', 'StomachS_1_end',
    'StomachS_2_end', 'ChestF_end', 'StomachF_end', 'PelvisF_end',
    'HeadS_1_end', 'HeadS_2_end', 'HeadF_end', 'Heel_1_end', 'Heel_2_end',
    'ToeS_1_end', 'ToeS_2_end',
    'Hand_1_1_end', 'Hand_1_2_end', 'Knuckles_1_1_end', 'Knuckles_1_2_end',
    'Fingers_1_1_end', 'Fingers_1_2_end', 'Fingertips_1_1_end', 'Fingertips_1_2_end',
    'Hand_2_1_end', 'Hand_2_2_end', 'Knuckles_2_1_end', 'Knuckles_2_2_end',
    'Fingers_2_1_end', 'Fingers_2_2_end', 'Fingertips_2_1_end', 'Fingertips_2_2_end',
    'WeaponF_l', 'WeaponS_l', 'WeaponDirection_l',
    'WeaponF_r', 'WeaponS_r', 'WeaponDirection_r',
})

NON_AIMABLE_NODES = frozenset({'COM_end'})

PRIMARY_CHILDREN = {'Pelvis': 'Stomach', 'Stomach': 'Chest', 'Chest': 'Neck', 'Neck': 'Head'}
for _side in ('1', '2'):
    for _parent, _child in (('Thigh', 'Calf'), ('Calf', 'Foot'), ('Foot', 'Toes'),
                            ('Arm', 'Forearm'), ('Forearm', 'Hand'), ('Hand', 'Fingers'), ('Fingers', 'Fingertips')):
        PRIMARY_CHILDREN[f'{_parent}_{_side}'] = f'{_child}_{_side}'
    PRIMARY_CHILDREN[f'Toes_{_side}'] = f'Toes_{_side}_end'
    PRIMARY_CHILDREN[f'Fingertips_{_side}'] = f'Fingertips_{_side}_1'

EPSILON = 1e-8

NODE_ORDER = [
    "HeadF",
    "Neck",
    "Arm_2",
    "Arm_1",
    "Forearm_2",
    "Forearm_1",
    "Hand_2",
    "Hand_1",
    "Fingertips_2_1",
    "Fingertips_1_1",
    "Thigh_2",
    "Thigh_1",
    "Calf_2",
    "Calf_1",
    "Foot_2",
    "Foot_1",
    "Toes_2",
    "Toes_1",
    "Pelvis",
    "WeaponF_l",
    "ArmatureWeaponLeft",
    "WeaponS_l",
    "WeaponDirection_l",
    "WeaponF_r",
    "ArmatureWeaponRight",
    "WeaponS_r",
    "WeaponDirection_r",
    "Stomach",
    "Chest",
    "Toes_2_end",
    "Heel_2_end",
    "Heel_1_end",
    "ToeS_2_end",
    "Toes_1_end",
    "ToeS_1_end",
    "Fingers_2",
    "Knuckles_2_1_end",
    "Fingers_1",
    "Knuckles_1_1_end",
    "Fingertips_2",
    "Fingertips_1",
    "Fingers_2_1_end",
    "Fingers_1_1_end",
    "Head",
    "ChestS_2_end",
    "ChestS_1_end",
    "StomachS_2_end",
    "StomachS_1_end",
    "ChestF_end",
    "StomachF_end",
    "PelvisF_end",
    "HeadS_2_end",
    "HeadS_1_end",
    "HeadF_end",
    "COM_end",
    "Hand_2_1_end",
    "Hand_2_2_end",
    "Knuckles_2_2_end",
    "Fingers_2_2_end",
    "Fingertips_2_1_end",
    "Fingertips_2_2_end",
    "Hand_1_1_end",
    "Hand_1_2_end",
    "Knuckles_1_2_end",
    "Fingers_1_2_end",
    "Fingertips_1_1_end",
    "Fingertips_1_2_end",
]

NODE_COUNT = len(NODE_ORDER)
NODE_SET = frozenset(NODE_ORDER)
if len(NODE_SET) != NODE_COUNT:
    raise ValueError("NODE_ORDER contains duplicate names")
if not ROTATION_HELPERS <= NODE_SET:
    raise ValueError(f"ROTATION_HELPERS not in NODE_ORDER: {sorted(ROTATION_HELPERS - NODE_SET)}")


def command_name():
    return "Gymnast Tool Suite.Shadow Fight 2.Import Animation"


def command_description():
    return "Import Shadow Fight 2 Animation by selecting .bin files"


def decode_bin(data):
    """Read a BIN file and return its animation frames."""

    if len(data) < 4:
        raise ValueError("BIN is missing its frame count")

    frame_count = int.from_bytes(
        data[:4],
        'little',
        signed=True,
    )

    if frame_count <= 0:
        raise ValueError(f"Invalid BIN frame count: {frame_count}")

    frames = np.empty(
        (frame_count, NODE_COUNT, 3),
        dtype=np.float64,
    )

    offset = 4

    for frame_index in range(frame_count):
        if offset + 5 > len(data):
            raise ValueError(
                f"BIN is truncated at frame {frame_index}: "
                "missing frame header"
            )

        node_count = int.from_bytes(
            data[offset + 1:offset + 5],
            'little',
            signed=True,
        )

        if node_count < 0:
            raise ValueError(
                f"Invalid node count at BIN frame {frame_index}: {node_count}"
            )

        if node_count < NODE_COUNT:
            raise ValueError(
                f"BIN frame {frame_index} contains only {node_count} nodes, "
                f"but this Cascadeur rig requires at least {NODE_COUNT}"
            )

        payload_size = 12 * node_count
        payload_start = offset + 5
        payload_end = payload_start + payload_size

        if payload_end > len(data):
            raise ValueError(
                f"BIN is truncated at frame {frame_index}: "
                f"header says {node_count} nodes ({payload_size} bytes), "
                "but the file ends early"
            )

        frame_nodes = np.frombuffer(
            data,
            dtype='<f4',
            count=node_count * 3,
            offset=payload_start,
        ).reshape(node_count, 3)

        # A BIN may contain more nodes than the rig uses.
        frames[frame_index] = frame_nodes[:NODE_COUNT]
        offset = payload_end

    if offset != len(data):
        extra_bytes = len(data) - offset
        raise ValueError(
            f"BIN contains {extra_bytes} unexpected bytes "
            "after the final animation frame"
        )

    if not np.isfinite(frames).all():
        raise ValueError("BIN contains NaN or infinite positions")

    return frames


def vector_length(vector):
    return math.sqrt(vector @ vector)


def cross_product(first, second):
    return np.array((
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    ))


def unit_vector(vector):
    length = vector_length(vector)

    if not math.isfinite(length) or length < EPSILON:
        raise ValueError(
            "Cannot orient a collapsed bone or zero-length direction"
        )

    return vector / length


def rotation_matrix(axis, cosine, sine):
    x, y, z = axis.tolist()
    t = 1.0 - cosine

    return np.array((
        (
            cosine + t * x * x,
            t * x * y - sine * z,
            t * x * z + sine * y,
        ),
        (
            t * x * y + sine * z,
            cosine + t * y * y,
            t * y * z - sine * x,
        ),
        (
            t * x * z - sine * y,
            t * y * z + sine * x,
            cosine + t * z * z,
        ),
    ))


def swing_rotation(source, target):
    source = unit_vector(source)
    target = unit_vector(target)

    cross = cross_product(source, target)
    sine = vector_length(cross)
    cosine = min(1.0, max(-1.0, float(source @ target)))

    if sine < EPSILON:
        if cosine > 0:
            return np.eye(3)

        axis = cross_product(
            source,
            np.eye(3)[np.argmin(np.abs(source))],
        )
        return rotation_matrix(unit_vector(axis), -1.0, 0.0)

    length = math.hypot(sine, cosine)

    return rotation_matrix(
        cross / sine,
        cosine / length,
        sine / length,
    )


def solve_rotation(
    reference,
    primary_local,
    primary_target,
    helper_local,
    helper_target,
):
    valid_pairs = [
        (local, target)
        for local, target in zip(helper_local, helper_target)
        if vector_length(local) > EPSILON
        and vector_length(target) > EPSILON
    ]

    if primary_local is not None:
        target_axis = unit_vector(primary_target)
        rotation = (
            swing_rotation(reference @ primary_local, target_axis)
            @ reference
        )

        cosine = 0.0
        sine = 0.0

        for local, target in valid_pairs:
            source_vector = rotation @ local
            source_vector -= target_axis * (target_axis @ source_vector)

            target_vector = target - target_axis * (target_axis @ target)

            cosine += source_vector @ target_vector
            sine += target_axis @ cross_product(
                source_vector,
                target_vector,
            )

        twist_length = math.hypot(cosine, sine)

        if twist_length < EPSILON:
            return rotation

        return (
            rotation_matrix(
                target_axis,
                cosine / twist_length,
                sine / twist_length,
            )
            @ rotation
        )

    if not valid_pairs:
        return reference.copy()

    source_vectors = np.array([
        local for local, _ in valid_pairs
    ])
    target_vectors = np.array([
        target for _, target in valid_pairs
    ])

    if (
        np.linalg.matrix_rank(source_vectors, tol=EPSILON) < 2
        or np.linalg.matrix_rank(target_vectors, tol=EPSILON) < 2
    ):
        source, target = max(
            valid_pairs,
            key=lambda pair: vector_length(pair[0]),
        )

        return (
            swing_rotation(reference @ source, target)
            @ reference
        )

    u, _, vt = np.linalg.svd(
        source_vectors.T @ target_vectors
    )

    correction = np.eye(3)
    correction[2, 2] = np.linalg.det(vt.T @ u.T)

    return vt.T @ correction @ u.T


class Rig:
    def __init__(self, nodes, ordered_nodes):
        self.nodes = nodes
        self.ordered_nodes = ordered_nodes

        self.parent = {
            name: node['parent']
            for name, node in nodes.items()
        }

        self.protected = frozenset(
            name
            for name in nodes
            if name in ROTATION_HELPERS or name not in NODE_SET
        )

        self.written = [
            name
            for name in ordered_nodes
            if name in NODE_SET and name not in ROTATION_HELPERS
        ]

        self.passive_ids = frozenset(
            nodes[name][data_key]
            for name in self.protected
            for data_key in ('local_pos_id', 'local_rot_id')
        )

        children = {
            name: []
            for name in ordered_nodes
        }

        for child in ordered_nodes:
            parent = self.parent[child]

            if parent is not None:
                children[parent].append(child)

        def sampled_children(name):
            found = []

            for child in children[name]:
                if child in NODE_SET:
                    found.append(child)
                else:
                    found.extend(sampled_children(child))

            return found

        self.plan = []

        for name in ordered_nodes:
            descendants = sampled_children(name)

            helpers = [
                child
                for child in descendants
                if child in ROTATION_HELPERS
            ]

            aimable_nodes = [
                child
                for child in descendants
                if child not in ROTATION_HELPERS
                and child not in NON_AIMABLE_NODES
            ]

            self.plan.append((
                name,
                self.parent[name],
                name in self.protected,
                helpers,
                aimable_nodes,
                PRIMARY_CHILDREN.get(name),
            ))


def resolve_rig(scene):
    model_viewer = scene.model_viewer()
    behaviour_viewer = model_viewer.behaviour_viewer()

    nodes = {}

    def read_node(name, object_id):
        transform = behaviour_viewer.get_behaviour_by_name(
            object_id,
            'Transform',
        )
        basic = behaviour_viewer.get_behaviour_by_name(
            object_id,
            'Basic',
        )

        if transform.is_null() or basic.is_null():
            raise ValueError(
                f"Missing Transform or Basic behaviour on {name}"
            )

        node = {
            'id': object_id,
            'parent_id': behaviour_viewer.get_behaviour_object(
                basic,
                'parent',
            ),
        }

        for field_name, property_name in (
            ('pos_id', 'global_position'),
            ('rot_id', 'global_rotation'),
            ('local_pos_id', 'local_position'),
            ('local_rot_id', 'local_rotation'),
        ):
            data_id = behaviour_viewer.get_behaviour_data(
                transform,
                property_name,
            )

            if data_id is None or data_id.is_null():
                raise ValueError(
                    f"Missing {property_name} on {name}"
                )

            node[field_name] = data_id

        return node

    for name in NODE_ORDER:
        object_ids = model_viewer.get_objects(name)

        if len(object_ids) != 1:
            raise ValueError(
                f"Expected exactly one node named {name}; "
                f"found {len(object_ids)}"
            )

        nodes[name] = read_node(name, object_ids[0])

    # Some rig bones sit between the BIN nodes.
    node_names_by_id = {
        node['id']: name
        for name, node in nodes.items()
    }

    for name in NODE_ORDER:
        parent_id = nodes[name]['parent_id']
        chain = []
        seen = {nodes[name]['id']}

        while not parent_id.is_null() and parent_id not in node_names_by_id:
            if parent_id in seen:
                raise ValueError(
                    f"Cycle in the rig hierarchy above {name}"
                )

            seen.add(parent_id)

            parent_name = model_viewer.get_object_name(parent_id)
            basic = behaviour_viewer.get_behaviour_by_name(
                parent_id,
                'Basic',
            )

            if basic.is_null():
                raise ValueError(
                    f"Missing Basic behaviour on ancestor {parent_name}"
                )

            chain.append((parent_name, parent_id))
            parent_id = behaviour_viewer.get_behaviour_object(
                basic,
                'parent',
            )

        if parent_id in node_names_by_id:
            for parent_name, object_id in reversed(chain):
                if (
                    parent_name in nodes
                    and nodes[parent_name]['id'] != object_id
                ):
                    raise ValueError(
                        f"Ambiguous ancestor name: {parent_name}"
                    )

                nodes[parent_name] = read_node(
                    parent_name,
                    object_id,
                )
                node_names_by_id[object_id] = parent_name

    for name, node in nodes.items():
        node['parent'] = node_names_by_id.get(node['parent_id'])

        if (
            name in ROTATION_HELPERS
            and node['parent'] is None
        ):
            raise ValueError(
                f"Helper {name} has no ancestor connected to the BIN rig"
            )

    ordered_nodes = []
    completed = set()
    pending = list(nodes)

    while pending:
        ready = [
            name
            for name in pending
            if (
                nodes[name]['parent'] is None
                or nodes[name]['parent'] in completed
            )
        ]

        if not ready:
            raise ValueError("Cycle in the rig hierarchy")

        ordered_nodes.extend(ready)
        completed.update(ready)

        ready = set(ready)
        pending = [
            name
            for name in pending
            if name not in ready
        ]

    return Rig(nodes, ordered_nodes)


def read_reference_pose(data_viewer, rig, frame):
    positions = {}
    rotations = {}

    for name, node in rig.nodes.items():
        try:
            position = np.array(
                data_viewer.get_data_value(
                    node['pos_id'],
                    frame,
                ),
                dtype=np.float64,
            ).reshape(3)

            rotation = np.array(
                data_viewer.get_data_value(
                    node['rot_id'],
                    frame,
                ).to_rotation_matrix(),
                dtype=np.float64,
            )

            if not (
                np.isfinite(position).all()
                and np.isfinite(rotation).all()
            ):
                raise ValueError("non-finite transform")

        except (RuntimeError, ValueError, TypeError) as exc:
            raise ValueError(
                f"Cannot read reference pose for "
                f"{name} at frame {frame}: {exc}"
            ) from exc

        positions[name] = position
        rotations[name] = rotation

    reference = {}

    for (
        name,
        parent,
        passive,
        helpers,
        aimable_nodes,
        primary_hint,
    ) in rig.plan:
        world_rotation = rotations[name]
        world_position = positions[name]

        position_offset = None

        if parent is None:
            relative_rotation = world_rotation
        else:
            parent_rotation = rotations[parent].T
            relative_rotation = parent_rotation @ world_rotation

            if passive:
                position_offset = (
                    parent_rotation
                    @ (world_position - positions[parent])
                )

        primary = (
            primary_hint
            if primary_hint in aimable_nodes
            else max(
                aimable_nodes,
                key=lambda child: vector_length(
                    positions[child] - world_position
                ),
                default=None,
            )
        )

        local_axis = (
            None
            if primary is None
            else world_rotation.T
            @ (positions[primary] - world_position)
        )

        local_helpers = [
            world_rotation.T @ (positions[child] - world_position)
            for child in helpers
        ]

        reference[name] = (
            position_offset,
            relative_rotation,
            primary,
            local_axis,
            local_helpers,
        )

    return reference


def solve_frame(rig, reference, targets):
    actual_positions = {}
    evaluated_rotations = {}
    solved_rotations = {}

    for (
        name,
        parent,
        passive,
        helpers,
        _,
        _,
    ) in rig.plan:
        (
            position_offset,
            relative_rotation,
            primary,
            local_axis,
            local_helpers,
        ) = reference[name]

        if passive:
            origin = (
                actual_positions[parent]
                + evaluated_rotations[parent] @ position_offset
            )
        else:
            origin = targets[name]

        actual_positions[name] = origin

        world_reference = (
            relative_rotation
            if parent is None
            else evaluated_rotations[parent] @ relative_rotation
        )

        if primary is None and not helpers:
            evaluated_rotations[name] = world_reference
            continue

        primary_target = (
            None
            if primary is None
            else targets[primary] - origin
        )

        helper_targets = [
            targets[child] - origin
            for child in helpers
        ]

        try:
            solved_rotations[name] = evaluated_rotations[name] = (
                solve_rotation(
                    world_reference,
                    local_axis,
                    primary_target,
                    local_helpers,
                    helper_targets,
                )
            )
        except ValueError as exc:
            raise ValueError(
                f"Cannot orient {name}: {exc}"
            ) from exc

    helper_errors = {
        name: vector_length(
            actual_positions[name] - targets[name]
        )
        for name in ROTATION_HELPERS
    }

    positions_to_write = {
        name: actual_positions[name]
        for name in rig.written
    }

    return (
        positions_to_write,
        solved_rotations,
        helper_errors,
        evaluated_rotations,
    )


def split_rotation_writes(rig, rotations, evaluated_rotations):
    global_rotations = {}
    local_rotations = {}

    for name, rotation in rotations.items():
        if name not in rig.protected:
            global_rotations[name] = rotation
            continue

        parent = rig.parent[name]

        if parent is None:
            raise ValueError(
                f"Missing parent for protected rotation: {name}"
            )

        local_rotations[name] = (
            evaluated_rotations[parent].T @ rotation
        )

    return global_rotations, local_rotations


def write_frame(
    editor,
    updater,
    rig,
    positions,
    rotations,
    frame,
    local_rotations,
):
    if not rig.protected.isdisjoint(rotations):
        raise ValueError(
            "Protected bones must use local rotations, "
            "never global rotation writes"
        )

    invalid_positions = rig.protected.intersection(positions)

    if invalid_positions:
        raise ValueError(
            "Refusing to write a helper or intermediate bone position: "
            f"{min(invalid_positions)}"
        )

    set_value = editor.set_data_value
    nodes = rig.nodes

    updated_data = set(rig.passive_ids)

    for name, position in positions.items():
        data_id = nodes[name]['pos_id']

        set_value(
            data_id,
            frame,
            position.astype(np.float32),
        )
        updated_data.add(data_id)

    make_rotation = csc.math.Rotation.from_rotation_matrix

    for name, rotation in rotations.items():
        data_id = nodes[name]['rot_id']

        set_value(
            data_id,
            frame,
            make_rotation(rotation.astype(np.float32)),
        )
        updated_data.add(data_id)

    for name, rotation in local_rotations.items():
        data_id = nodes[name]['local_rot_id']

        set_value(
            data_id,
            frame,
            make_rotation(rotation.astype(np.float32)),
        )
        updated_data.add(data_id)

    updater.run_update(updated_data, frame)


def get_bin_limb_direction(
    positions,
    chain,
    reference_direction,
):
    start, bend, end = [
        np.asarray(
            positions[name],
            dtype=np.float64,
        )
        for name in chain
    ]

    reference = np.asarray(
        reference_direction,
        dtype=np.float64,
    )

    reference_length = float(
        np.linalg.norm(reference)
    )

    if reference_length < EPSILON:
        raise ValueError(
            "Limb controller has a zero-length direction"
        )

    axis = end - start
    reach = float(np.linalg.norm(axis))

    if reach < EPSILON:
        return reference.copy()

    axis /= reach

    pole = bend - start
    pole -= axis * np.dot(pole, axis)

    if np.linalg.norm(pole) <= 1e-6 * max(
        reach,
        np.linalg.norm(bend - start),
        1.0,
    ):
        pole = (
            reference
            - axis * np.dot(reference, axis)
        )

        if np.linalg.norm(pole) < EPSILON:
            return reference.copy()

    return unit_vector(pole) * reference_length


def find_direction_controllers(scene, nodes):
    model_viewer = scene.model_viewer()
    behaviour_viewer = model_viewer.behaviour_viewer()
    data_viewer = model_viewer.data_viewer()

    imported_node_ids = {
        node['id']
        for node in nodes.values()
    }

    limb_chains = {
        f'{middle}_{side}': (
            f'{first}_{side}',
            f'{middle}_{side}',
            f'{last}_{side}',
        )
        for side in ('1', '2')
        for first, middle, last in (
            ('Arm', 'Forearm', 'Hand'),
            ('Thigh', 'Calf', 'Foot'),
        )
    }

    controllers = {}

    for info in behaviour_viewer.get_behaviours('RigAdditionalInfo'):
        joint = behaviour_viewer.get_behaviour_reference(
            info,
            'joint',
        )

        if (
            joint.is_null()
            or behaviour_viewer.get_behaviour_owner(joint)
            not in imported_node_ids
        ):
            continue

        limb = behaviour_viewer.get_behaviour_reference(
            info,
            'limb_direction',
        )

        if limb.is_null():
            continue

        controller_id = behaviour_viewer.get_behaviour_owner(limb)
        active_id = behaviour_viewer.get_behaviour_setting(
            limb,
            'is_active',
        )
        direction_id = data_viewer.get_data_id(
            controller_id,
            'Direction',
        )
        name = model_viewer.get_object_name(controller_id)

        if active_id.is_null() or direction_id.is_null():
            raise ValueError(
                f"Missing active setting or Direction channel on {name}"
            )

        joint_name = model_viewer.get_object_name(
            behaviour_viewer.get_behaviour_owner(joint)
        )

        chain = limb_chains.get(joint_name)

        if chain is None:
            raise ValueError(
                "Unexpected direction controller joint in this fixed rig: "
                f"{joint_name}"
            )

        offset_id = data_viewer.get_data_id(
            controller_id,
            'Offset',
        )

        if offset_id.is_null():
            raise ValueError(
                f"Missing Offset channel on {name}"
            )

        controllers[controller_id] = {
            'id': controller_id,
            'name': name,
            'active_id': active_id,
            'direction_id': direction_id,
            'offset_id': offset_id,
            'chain': chain,
        }

    return list(controllers.values())


def write_frame_with_controllers(
    editor,
    data_viewer,
    updater,
    rig,
    positions,
    rotations,
    local_rotations,
    frame,
    controllers,
    active_states,
):
    if not controllers:
        write_frame(
            editor,
            updater,
            rig,
            positions,
            rotations,
            frame,
            local_rotations,
        )
        return

    directions = {}

    try:
        for controller in controllers:
            editor.set_setting_value(
                controller['active_id'],
                frame,
                False,
            )

            editor.set_data_value(
                controller['offset_id'],
                frame,
                0.0,
            )

        updater.generate_update()

        write_frame(
            editor,
            updater,
            rig,
            positions,
            rotations,
            frame,
            local_rotations,
        )

        for controller in controllers:
            direction = np.asarray(
                data_viewer.get_data_value(
                    controller['direction_id'],
                    frame,
                ),
                dtype=np.float32,
            ).reshape(3)

            if not np.isfinite(direction).all():
                raise RuntimeError(
                    f"Non-finite direction generated for "
                    f"{controller['name']} at frame {frame}"
                )

            directions[controller['direction_id']] = (
                get_bin_limb_direction(
                    positions,
                    controller['chain'],
                    direction,
                )
            )

    finally:
        for controller in controllers:
            editor.set_setting_value(
                controller['active_id'],
                frame,
                active_states[controller['active_id']],
            )

        updater.generate_update()

    active_directions = set()

    for controller in controllers:
        direction_id = controller['direction_id']

        editor.set_data_value(
            direction_id,
            frame,
            directions[direction_id],
        )

        if active_states[controller['active_id']]:
            active_directions.add(direction_id)

    if active_directions:
        updater.run_update(
            active_directions,
            frame,
        )


def import_animation(scene, filepath):
    frames = decode_bin(
        Path(filepath).read_bytes()
    )

    start_frame = scene.get_current_frame(False)

    if start_frame < 0:
        raise ValueError(
            "Import start frame must be nonnegative"
        )

    rig = resolve_rig(scene)
    controllers = find_direction_controllers(
        scene,
        rig.nodes,
    )

    model_viewer = scene.model_viewer()
    data_viewer = model_viewer.data_viewer()

    animation_size = data_viewer.get_animation_size()

    if animation_size < 1:
        raise ValueError(
            "Scene has no reference animation frame"
        )

    layer_viewer = scene.layers_viewer()
    layers = set()

    for name, node in rig.nodes.items():
        layer_id = layer_viewer.layer_id_by_obj_id(
            node['id']
        )

        if (
            layer_id.is_null()
            or layer_viewer.layer(layer_id).is_locked
        ):
            raise ValueError(
                f"Missing or locked animation layer for {name}"
            )

        layers.add(layer_id)

    for controller in controllers:
        layer_id = layer_viewer.layer_id_by_obj_id(
            controller['id']
        )

        if (
            layer_id.is_null()
            or layer_viewer.layer(layer_id).is_locked
        ):
            raise ValueError(
                f"Missing or locked controller layer "
                f"for {controller['name']}"
            )

        layers.add(layer_id)

    plans = []
    worst_error = (0.0, '', start_frame)

    reference_frame = None
    reference_pose = None
    controller_states = None

    for index, frame_values in enumerate(frames):
        frame = start_frame + index

        read_frame = min(
            frame,
            animation_size - 1,
        )

        if read_frame != reference_frame:
            reference_frame = read_frame
            reference_pose = read_reference_pose(
                data_viewer,
                rig,
                read_frame,
            )

            controller_states = {
                controller['active_id']: bool(
                    data_viewer.get_setting_value(
                        controller['active_id'],
                        read_frame,
                    )
                )
                for controller in controllers
            }

        targets = dict(
            zip(NODE_ORDER, frame_values)
        )

        try:
            (
                positions,
                rotations,
                errors,
                evaluated_rotations,
            ) = solve_frame(
                rig,
                reference_pose,
                targets,
            )

            (
                rotations,
                local_rotations,
            ) = split_rotation_writes(
                rig,
                rotations,
                evaluated_rotations,
            )

        except ValueError as exc:
            raise ValueError(
                f"BIN frame {index}, scene frame {frame}: {exc}"
            ) from exc

        for name, error in errors.items():
            if error > worst_error[0]:
                worst_error = (
                    error,
                    name,
                    frame,
                )

        plans.append((
            positions,
            rotations,
            local_rotations,
            controller_states,
        ))

    writable_channels = {
        rig.nodes[name]['pos_id']
        for name in rig.written
    }

    writable_channels.update(
        rig.nodes[name]['rot_id']
        for name in set().union(
            *(plan[1] for plan in plans)
        )
    )

    writable_channels.update(
        rig.nodes[name]['local_rot_id']
        for name in set().union(
            *(plan[2] for plan in plans)
        )
    )

    writable_channels.update(
        controller['direction_id']
        for controller in controllers
    )

    writable_channels.update(
        controller['offset_id']
        for controller in controllers
    )

    for data_id in writable_channels:
        if (
            data_viewer.get_data(data_id).mode
            != csc.model.DataMode.Animation
        ):
            raise ValueError(
                "Import requires animated position/rotation channels; "
                "a target channel is static"
            )

    helper_slots = [
        (
            name,
            rig.nodes[name]['pos_id'],
            NODE_ORDER.index(name),
        )
        for name in ROTATION_HELPERS
    ]

    def modify(model, update, updater):
        nonlocal worst_error

        end_frame = (
            start_frame
            + len(plans)
            - 1
        )

        layer_editor = model.layers_editor()

        if end_frame >= animation_size:
            for layer_id in layers:
                layer_editor.set_section(
                    csc.layers.layer.Section(),
                    end_frame,
                    layer_id,
                )

            model.fit_animation_size_by_layers()

            if data_viewer.get_animation_size() <= end_frame:
                raise RuntimeError(
                    f"Could not extend animation through frame {end_frame}"
                )

        key_if_needed = (
            layer_editor.set_fixed_interpolation_or_key_if_need
        )

        for frame in range(
            start_frame,
            end_frame + 1,
        ):
            for layer_id in layers:
                key_if_needed(
                    layer_id,
                    frame,
                    True,
                )

        layer_editor.normalize_sections(scene)
        updater.generate_update()

        editor = model.data_editor()

        for index, (
            positions,
            rotations,
            local_rotations,
            states,
        ) in enumerate(plans):
            frame = start_frame + index

            write_frame_with_controllers(
                editor,
                data_viewer,
                updater,
                rig,
                positions,
                rotations,
                local_rotations,
                frame,
                controllers,
                states,
            )

            for name, position_id, node_index in helper_slots:
                actual_position = np.asarray(
                    data_viewer.get_data_value(
                        position_id,
                        frame,
                    ),
                    dtype=np.float64,
                ).reshape(3)

                error = vector_length(
                    actual_position
                    - frames[index, node_index]
                )

                if not math.isfinite(error):
                    raise RuntimeError(
                        "Rig evaluation produced a non-finite "
                        f"helper position: {name}"
                    )

                if error > worst_error[0]:
                    worst_error = (
                        error,
                        name,
                        frame,
                    )

    if not scene.modify_update(
        command_name(),
        modify,
    ):
        raise RuntimeError(
            "Cascadeur did not complete the BIN import; "
            "check the event log"
        )

    if worst_error[0] > 1e-4:
        scene.warning(
            "Helper targets are not exactly reachable with the "
            "existing rig offsets. "
            f"Largest residual: {worst_error[0]:.6g} scene units, "
            f"{worst_error[1]}, frame {worst_error[2]}. "
            "Helper and intermediate position channels were not written."
        )

    scene.info(
        f"Imported {len(frames)} BIN frames "
        f"starting at {start_frame}"
    )

    if controllers:
        scene.info(
            f"Synchronized {len(controllers)} limb direction controllers; "
            "original enable states restored"
        )


def run(scene):
    def load(filepath):
        if not filepath:
            return

        try:
            import_animation(
                scene,
                filepath,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            scene.error(
                f"BIN import failed: {exc}"
            )

    csc.app.get_application().get_file_dialog_manager().show_open_file_dialog(
        'Import Shadow Fight 2 animation BIN',
        '',
        ['*.bin'],
        load,
    )