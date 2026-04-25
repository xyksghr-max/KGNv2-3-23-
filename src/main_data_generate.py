import argparse
import os
from cv2 import split

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import random

import _init_paths

from utils.configs import load_config
from data_generation import SceneRender, Cuboid, Cylinder, Sphere
from data_generation.dataLogger import DataLogger
from utils.transform import create_homog_matrix
from utils.file import read_numList_from_file, write_numList_to_file

# global
OBJ_NAMES = ["cuboid", "bowl", "sphere", "cylinder", "ring", "stick"]
GEOM_OBJ_NAMES = ["cuboid", "cylinder", "ring", "stick"]

class ObjSampler():
    """The sampler for creating the object with the sampled attributes
    """
    def __init__(self, 
        cuboid_size_range, 
        sphere_radius_range,
        bowl_radius_range,
        cylinder_rin_range,
        cylinder_h_range,
        ring_rin_range,
        ring_h_range,
        stick_rin_range,
        stick_h_range,
        geom_enhance_config=None
    ):
        self.cuboid_size_range = cuboid_size_range
        self.sphere_radius_range = sphere_radius_range
        self.bowl_radius_range = bowl_radius_range
        self.cylinder_rin_range = cylinder_rin_range
        self.cylinder_h_range = cylinder_h_range
        self.ring_rin_range = ring_rin_range
        self.ring_h_range = ring_h_range
        self.stick_rin_range = stick_rin_range
        self.stick_h_range = stick_h_range
        self.geom_enhance_config = geom_enhance_config or {}
    
    def _get_geom_range(self, key, fallback):
        return self.geom_enhance_config.get(key, fallback)

    def _sample_extreme_cuboid_dims(self):
        """Sample a cuboid with a stronger aspect-ratio variation.

        The object type remains ``cuboid`` so the original cuboid grasp family,
        reconstruction, loader, and evaluator paths stay unchanged.
        """
        profiles = self.geom_enhance_config.get("cuboid_profiles", None)
        if profiles is None:
            profiles = [
                {
                    "name": "long_bar",
                    "dims": [[0.12, 0.20], [0.015, 0.04], [0.025, 0.06]],
                },
                {
                    "name": "thin_plate",
                    "dims": [[0.08, 0.16], [0.06, 0.12], [0.008, 0.02]],
                },
                {
                    "name": "flat_box",
                    "dims": [[0.08, 0.14], [0.05, 0.10], [0.015, 0.035]],
                },
            ]

        profile = random.choice(profiles)
        dims = [
            np.random.uniform(dim_range[0], dim_range[1])
            for dim_range in profile["dims"]
        ]
        random.shuffle(dims)
        return dims

    def sample_obj(self, obj_type, geom_enhanced=False):
        color = np.random.choice(range(256), size=3)
        # color = np.array([24, 237, 234])    # for rendering a prettier object in the paper
        if obj_type == "cuboid":
            if geom_enhanced:
                x, y, z = self._sample_extreme_cuboid_dims()
            else:
                x = np.random.uniform(self.cuboid_size_range[0], self.cuboid_size_range[1])
                y = np.random.uniform(self.cuboid_size_range[0], self.cuboid_size_range[1])
                z = np.random.uniform(self.cuboid_size_range[0], self.cuboid_size_range[1])
            obj = Cuboid(x, y, z, color=color)
        elif obj_type == "sphere":
            r = np.random.uniform(self.sphere_radius_range[0], self.sphere_radius_range[1])
            obj = Sphere(r=r, pose=create_homog_matrix(T_vec=[0, 0, r]), color=color)  # for sphere, create init pose to move it above the table
        elif obj_type == "bowl":
            r = np.random.uniform(self.bowl_radius_range[0], self.bowl_radius_range[1])
            obj = Sphere(r=r, semiSphere=True, pose=create_homog_matrix(T_vec=[0, 0, r]), color=color) # for semi-sphere, create init pose to move it above the table
        elif obj_type == "cylinder":
            r_range = self._get_geom_range("cylinder_rin_range", self.cylinder_rin_range) if geom_enhanced else self.cylinder_rin_range
            h_range = self._get_geom_range("cylinder_h_range", self.cylinder_h_range) if geom_enhanced else self.cylinder_h_range
            r_in = np.random.uniform(r_range[0], r_range[1])
            height = np.random.uniform(h_range[0], h_range[1])
            obj = Cylinder(r_in=r_in, height=height, color=color)
        elif obj_type == "ring":
            r_range = self._get_geom_range("ring_rin_range", self.ring_rin_range) if geom_enhanced else self.ring_rin_range
            h_range = self._get_geom_range("ring_h_range", self.ring_h_range) if geom_enhanced else self.ring_h_range
            r_in = np.random.uniform(r_range[0], r_range[1])
            height = np.random.uniform(h_range[0], h_range[1])
            obj = Cylinder(r_in = r_in, height = height, mode="ring", color=color)
        elif obj_type == "stick":
            r_range = self._get_geom_range("stick_rin_range", self.stick_rin_range) if geom_enhanced else self.stick_rin_range
            h_range = self._get_geom_range("stick_h_range", self.stick_h_range) if geom_enhanced else self.stick_h_range
            r_in = np.random.uniform(r_range[0], r_range[1])
            height = np.random.uniform(h_range[0], h_range[1])
            obj = Cylinder(r_in = r_in, height = height, mode="stick", color=color)
        else:
            raise NotImplementedError("The object type \"{}\" is not implemented".format(obj_type))

        return obj

def _should_use_geom_enhancement(object_config):
    geom_mode = object_config.get("geom_mode", "primitive")
    if geom_mode == "primitive":
        return False
    if geom_mode == "geom":
        return True
    if geom_mode == "mixed":
        return random.random() < float(object_config.get("geom_probability", 0.5))
    raise NotImplementedError("Unsupported geom_mode: {}".format(geom_mode))

def generate_and_write_split(total_scene_num, test_percentage, save_dir):
    """Generate the scene-wise train/test split and write the list out to a txt file
    """
    # train/test number
    test_num = round(total_scene_num * (test_percentage/100))

    # shuffle and split the scene index
    scene_idx = np.arange(total_scene_num)
    np.random.shuffle(scene_idx)
    test_idx, train_idx, _ = np.split(scene_idx, [test_num, total_scene_num])    

    # save out
    test_list_file = os.path.join(save_dir, "test.txt")
    train_list_file = os.path.join(save_dir, "train.txt")
    write_numList_to_file(train_list_file, train_idx) 
    write_numList_to_file(test_list_file, test_idx) 
      

def main(args, configs):
    # create the scene renderer, obj_sampler & the logger
    scene_renderer = SceneRender(
        table_size=configs["TABLE"]["size"],
        table_thickness=configs["TABLE"]["thickness"],
        camera=configs["CAMERA"]["intrinsic"],
        camera_num=configs["CAMERA"]["camera_num"],
        radius_range=configs["CAMERA"]["radius_range"],
        latitude_range=np.array(configs["CAMERA"]["latitude_range"])/180*np.pi      # convert from degree to radians
    )

    obj_sampler = ObjSampler(
        cuboid_size_range=configs["OBJECT"]["cuboid_size_range"],
        sphere_radius_range=configs["OBJECT"]["sphere_radius_range"],
        bowl_radius_range=configs["OBJECT"]["bowl_radius_range"],
        cylinder_rin_range=configs["OBJECT"]["cylinder_rin_range"],
        cylinder_h_range=configs["OBJECT"]["cylinder_h_range"],
        ring_rin_range=configs["OBJECT"]["ring_rin_range"],
        ring_h_range=configs["OBJECT"]["ring_h_range"],
        stick_rin_range=configs["OBJECT"]["stick_rin_range"],
        stick_h_range=configs["OBJECT"]["stick_h_range"],
        geom_enhance_config=configs["OBJECT"].get("GEOM_ENHANCE", {}),
    )
    geom_mode = configs["OBJECT"].get("geom_mode", "primitive")
    if geom_mode != "primitive":
        print("T6 geometry enhancement mode: {} (prob={})".format(
            geom_mode, configs["OBJECT"].get("geom_probability", "n/a")
        ))

    logger = DataLogger(logging_directory=configs["SAVE_PATH"])

    # iterate through the iteration number
    # obj_names = ["stick"]
    tqdm_bar = tqdm(total=configs["CARDINALITY"]["scene_num"])
    scene_count = 0
    while(scene_count < configs["CARDINALITY"]["scene_num"]):
        tqdm_bar.set_description( "Genrating the {}th scene".format(scene_count))
        np.random.seed(scene_count)

        # re-create the scenes
        scene_renderer.clear_objs()
        scene_renderer.resample_camera_poses()
        obj_list = []
        sample_pose = []
        resample_loc = []

        # determine the scene objects
        if configs["OBJECT"]["mode"] == "all":
            obj_names_scene = OBJ_NAMES 
            geom_flags_scene = [
                _should_use_geom_enhancement(configs["OBJECT"]) and obj_name in GEOM_OBJ_NAMES
                for obj_name in obj_names_scene
            ]
        elif configs["OBJECT"]["mode"] == "single":
            use_geom = _should_use_geom_enhancement(configs["OBJECT"])
            obj_pool = configs["OBJECT"].get("geom_obj_names", GEOM_OBJ_NAMES) if use_geom else OBJ_NAMES
            obj_names_scene = [random.choice(obj_pool)]
            geom_flags_scene = [use_geom and obj_names_scene[0] in GEOM_OBJ_NAMES]
            # obj_names_scene = ["stick"]

        # add the objects
        obj_scene_pairs = list(zip(obj_names_scene, geom_flags_scene))
        random.shuffle(obj_scene_pairs)
        for idx, (obj_name, geom_enhanced) in enumerate(obj_scene_pairs):
            obj = obj_sampler.sample_obj(obj_name, geom_enhanced=geom_enhanced)
            obj_list.append(obj)
            # If sphere or semi-sphere, just sample the location instead of the orientation
            if obj_name == "sphere" or obj_name == "bowl":
                sample_pose.append(False)
                resample_loc.append(True)
            else:
                sample_pose.append(True)
                resample_loc.append(False)
        
        tqdm_bar.set_description( "Gnerating {}th scene - Adding objects...".format(scene_count))

        try:
           scene_renderer.add_objs(obj_list, sample_pose=sample_pose, resample_xy_loc=resample_loc)
        except:
           tqdm_bar.set_description( "Failed to add the object. Retrying...")
           continue
        
        
        tqdm_bar.set_description( "The scene is created...Rendering the images")

        # get info
        intrinsic, cam_poses, _ = scene_renderer.get_camera_infos(style="OpenCV")
        grasp_poses, open_widths, collides = scene_renderer.get_grasp_infos()
        obj_types, obj_dims, obj_poses = scene_renderer.get_obj_infos()
        colors, depths, ins_masks = scene_renderer.render_imgs(instance_masks=True)
        tqdm_bar.set_description("The image data rendered...Saving them out")

        # debug
        if args.debug:
            # 3d scene
            scene_renderer.vis_scene(grasp_mode=1, mode="trimesh", world_frame=True)
            # display images
            for color, depth, ins_mask in zip(colors, depths, ins_masks):
                f, axarr = plt.subplots(1, 3)
                im = axarr[0].imshow(color)
                #f.colorbar(im, ax=axarr[0])
                im = axarr[1].imshow(depth)
                #f.colorbar(im, ax=axarr[1])
                im = axarr[2].imshow(ins_mask)
                #f.colorbar(im, ax=axarr[2])
            plt.show()

        # save out the info
        logger.save_scene_data(scene_count, intrinsic, cam_poses, colors, depths, ins_masks, \
            grasp_poses, open_widths, grasp_collision=collides, \
            obj_types=obj_types, obj_dims=obj_dims, obj_poses=obj_poses)
        tqdm_bar.set_description("Scene data saved out.")

        # scene count
        scene_count = scene_count + 1
        tqdm_bar.update()
    
    print("\n\n Splitting into training and testing subset...")
    generate_and_write_split(configs["CARDINALITY"]["scene_num"], configs["CARDINALITY"]["test_percentage"], configs["SAVE_PATH"])
    print("Split completed.")


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_file', default="lib/data_generation/ps_grasp_single.yaml", help="The configuration file.")
    parser.add_argument('--debug', action="store_true", help='If debug, will visualize the generated scene')
    parser.add_argument('--arg_configs', nargs="*", type=str, default=[], help='overwrite config parameters')
    args = parser.parse_args()
    print(args)

    configs = load_config(args.config_file)

    main(args, configs)
