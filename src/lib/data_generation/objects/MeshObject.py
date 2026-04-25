import os
from copy import deepcopy

import numpy as np
import trimesh

from .Base import Base


class MeshObject(Base):
    """A mesh-backed object whose grasp family comes from external labels."""

    def __init__(
        self,
        mesh_path,
        mesh_scale=1.0,
        grasp_poses=None,
        grasp_widths=None,
        color=np.array([80, 160, 230], dtype=np.uint8),
        pose=None,
        obj_type="mesh",
        mesh_meta=None,
    ):
        self.mesh_path = os.path.abspath(mesh_path)
        self.mesh_scale = float(mesh_scale)
        self._input_grasp_poses = np.asarray(grasp_poses, dtype=np.float64)
        self._input_grasp_widths = np.asarray(grasp_widths, dtype=np.float64)
        self.obj_type = obj_type
        self.mesh_meta = mesh_meta or {}
        if self._input_grasp_poses.ndim != 3 or self._input_grasp_poses.shape[1:] != (4, 4):
            raise ValueError("grasp_poses must have shape (N, 4, 4)")
        if self._input_grasp_widths.ndim != 1:
            raise ValueError("grasp_widths must have shape (N,)")
        if self._input_grasp_poses.shape[0] != self._input_grasp_widths.shape[0]:
            raise ValueError("grasp pose and width counts do not match")
        super().__init__(color=color, pose=pose)

    def generate_mesh(self):
        mesh = trimesh.load(self.mesh_path, force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        mesh = deepcopy(mesh)
        mesh.apply_scale(self.mesh_scale)
        if not isinstance(mesh, trimesh.Trimesh):
            raise ValueError("Unsupported mesh type loaded from {}".format(self.mesh_path))
        return mesh

    def generate_grasp_family(self):
        return self._input_grasp_poses.copy(), self._input_grasp_widths.copy()

    def get_obj_type(self):
        return self.obj_type

    def get_obj_dims(self):
        return np.asarray(self.obj_mesh.bounding_box.extents, dtype=np.float64)

    def get_mesh_meta(self):
        meta = dict(self.mesh_meta)
        meta.update(
            {
                "mesh_path": self.mesh_path,
                "mesh_scale": self.mesh_scale,
                "obj_type": self.obj_type,
                "obj_dims": self.get_obj_dims().tolist(),
                "grasp_count": int(self._input_grasp_poses.shape[0]),
            }
        )
        return meta

