import json
import yaml
import argparse
import os
import sys
sys.path.insert(0, '/home/dylangoetting/SpatialBenchmark')
# print("Current Working Directory:", os.getcwd())
from src.benchmark import *
from src.llavaAgent import *
import h5py
import pickle

if __name__ == '__main__':
    
    # use argparse to add the args "num_objects, num_samples, num_iterations, headless, offline, "
    parser = argparse.ArgumentParser(description="Create a dataset from sumulator")
    parser.add_argument('name', type=str, help='Name of dataset')
    parser.add_argument('--scene_ids', type=int, nargs='*', help='list of scene IDs', default=[800])
    parser.add_argument('--headless', type=bool, default=True)
    parser.add_argument('--resolution', type=list, help='camera resolution', default=(1080, 1920))
    parser.add_argument('--fov', type=int, help='fov of camera', default=90)
    parser.add_argument('--size', type=int, help='number of items in dataset', default=50)
    parser.add_argument('--max_objects', type=int, help='number of objects to annotate per image', default=5)

    args = parser.parse_args()

    files = os.listdir('scenes/hm3d/minival/')
    scene_paths = []
    simulators = []

    for f in files:
        try:
            if int(f[2:5]) in args.scene_ids:
                hsh = f[6:] 
                sim_kwargs = {'scene_path': f'scenes/hm3d/minival/00{f[2:5]}-{hsh}/{hsh}.basis.glb',
                            'scene_config': "scenes/hm3d/minival/hm3d_annotated_minival_basis.scene_dataset_config.json",
                            'resolution': args.resolution, 'headless': args.headless, 'fov': args.fov}
                s = AnnotatedSimulator(**sim_kwargs)
                s.scene_id = f[2:5]
                simulators.append(s)

        except:
            continue
    

    custom_dtype = np.dtype([
        ('image', np.uint8, (args.resolution[0], args.resolution[1], 4)),
        ('annotations', 'S5000'),  # JSON string, up to 1000 bytes
        ('fov', int),
        ('label', int),
        ('scene_id', 'S100')
    ])
    with h5py.File(f'annotated_datasets/{args.name}.hdf5', 'w') as f:
    # Create a group for images
    
        dataset = f.create_dataset("data", shape=(args.size,), dtype=custom_dtype)   

        for iter in range(args.size):
            sim = random.sample(simulators, 1)[0]
            while True:
                out = sim.step('r', num_objects=args.max_objects, annotate_image=False)
                if len(out['annotations']) == args.max_objects:
                    break
            image = out['image']
            image_float = image.astype('uint8')
            mdata = out['annotations']
            json_mdata = pickle.dumps(mdata)
            item = np.zeros((), dtype=custom_dtype)
            item['image'] = image_float
            item['annotations'] = json_mdata
            item['label'] = iter
            item['fov'] = args.fov
            item['scene_id'] = sim.scene_id
            dataset[iter] = item
            print(f'iter: {iter}')
