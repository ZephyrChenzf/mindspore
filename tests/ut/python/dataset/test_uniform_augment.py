# Copyright 2020 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import matplotlib.pyplot as plt
import numpy as np

import mindspore.dataset.engine as de
import mindspore.dataset.transforms.vision.c_transforms as C
import mindspore.dataset.transforms.vision.py_transforms as F
from mindspore import log as logger

DATA_DIR = "../data/dataset/testImageNetData/train/"


def visualize(image_original, image_ua):
    """
    visualizes the image using DE op and Numpy op
    """
    num = len(image_ua)
    for i in range(num):
        plt.subplot(2, num, i + 1)
        plt.imshow(image_original[i])
        plt.title("Original image")

        plt.subplot(2, num, i + num + 1)
        plt.imshow(image_ua[i])
        plt.title("DE UniformAugment image")

    plt.show()


def test_uniform_augment(plot=False, num_ops=2):
    """
    Test UniformAugment
    """
    logger.info("Test UniformAugment")

    # Original Images
    ds = de.ImageFolderDatasetV2(dataset_dir=DATA_DIR, shuffle=False)

    transforms_original = F.ComposeOp([F.Decode(),
                                       F.Resize((224, 224)),
                                       F.ToTensor()])

    ds_original = ds.map(input_columns="image",
                         operations=transforms_original())

    ds_original = ds_original.batch(512)

    for idx, (image, _) in enumerate(ds_original):
        if idx == 0:
            images_original = np.transpose(image, (0, 2, 3, 1))
        else:
            images_original = np.append(images_original,
                                        np.transpose(image, (0, 2, 3, 1)),
                                        axis=0)

            # UniformAugment Images
    ds = de.ImageFolderDatasetV2(dataset_dir=DATA_DIR, shuffle=False)

    transform_list = [F.RandomRotation(45),
                      F.RandomColor(),
                      F.RandomSharpness(),
                      F.Invert(),
                      F.AutoContrast(),
                      F.Equalize()]

    transforms_ua = F.ComposeOp([F.Decode(),
                                 F.Resize((224, 224)),
                                 F.UniformAugment(transforms=transform_list, num_ops=num_ops),
                                 F.ToTensor()])

    ds_ua = ds.map(input_columns="image",
                   operations=transforms_ua())

    ds_ua = ds_ua.batch(512)

    for idx, (image, _) in enumerate(ds_ua):
        if idx == 0:
            images_ua = np.transpose(image, (0, 2, 3, 1))
        else:
            images_ua = np.append(images_ua,
                                  np.transpose(image, (0, 2, 3, 1)),
                                  axis=0)

    num_samples = images_original.shape[0]
    mse = np.zeros(num_samples)
    for i in range(num_samples):
        mse[i] = np.mean((images_ua[i] - images_original[i]) ** 2)
    logger.info("MSE= {}".format(str(np.mean(mse))))

    if plot:
        visualize(images_original, images_ua)


def test_cpp_uniform_augment(plot=False, num_ops=2):
    """
    Test UniformAugment
    """
    logger.info("Test CPP UniformAugment")

    # Original Images
    ds = de.ImageFolderDatasetV2(dataset_dir=DATA_DIR, shuffle=False)

    transforms_original = [C.Decode(), C.Resize(size=[224, 224]),
                           F.ToTensor()]

    ds_original = ds.map(input_columns="image",
                         operations=transforms_original)

    ds_original = ds_original.batch(512)

    for idx, (image, _) in enumerate(ds_original):
        if idx == 0:
            images_original = np.transpose(image, (0, 2, 3, 1))
        else:
            images_original = np.append(images_original,
                                        np.transpose(image, (0, 2, 3, 1)),
                                        axis=0)

    # UniformAugment Images
    ds = de.ImageFolderDatasetV2(dataset_dir=DATA_DIR, shuffle=False)
    transforms_ua = [C.RandomCrop(size=[224, 224], padding=[32, 32, 32, 32]),
                     C.RandomHorizontalFlip(),
                     C.RandomVerticalFlip(),
                     C.RandomColorAdjust(),
                     C.RandomRotation(degrees=45)]

    uni_aug = C.UniformAugment(operations=transforms_ua, num_ops=num_ops)

    transforms_all = [C.Decode(), C.Resize(size=[224, 224]),
                      uni_aug,
                      F.ToTensor()]

    ds_ua = ds.map(input_columns="image",
                   operations=transforms_all, num_parallel_workers=1)

    ds_ua = ds_ua.batch(512)

    for idx, (image, _) in enumerate(ds_ua):
        if idx == 0:
            images_ua = np.transpose(image, (0, 2, 3, 1))
        else:
            images_ua = np.append(images_ua,
                                  np.transpose(image, (0, 2, 3, 1)),
                                  axis=0)
    if plot:
        visualize(images_original, images_ua)

    num_samples = images_original.shape[0]
    mse = np.zeros(num_samples)
    for i in range(num_samples):
        mse[i] = np.mean((images_ua[i] - images_original[i]) ** 2)
    logger.info("MSE= {}".format(str(np.mean(mse))))


def test_cpp_uniform_augment_exception_pyops(num_ops=2):
    """
    Test UniformAugment invalid op in operations
    """
    logger.info("Test CPP UniformAugment invalid OP exception")

    transforms_ua = [C.RandomCrop(size=[224, 224], padding=[32, 32, 32, 32]),
                     C.RandomHorizontalFlip(),
                     C.RandomVerticalFlip(),
                     C.RandomColorAdjust(),
                     C.RandomRotation(degrees=45),
                     F.Invert()]

    try:
        _ = C.UniformAugment(operations=transforms_ua, num_ops=num_ops)

    except Exception as e:
        logger.info("Got an exception in DE: {}".format(str(e)))
        assert "operations" in str(e)


def test_cpp_uniform_augment_exception_large_numops(num_ops=6):
    """
    Test UniformAugment invalid large number of ops
    """
    logger.info("Test CPP UniformAugment invalid large num_ops exception")

    transforms_ua = [C.RandomCrop(size=[224, 224], padding=[32, 32, 32, 32]),
                     C.RandomHorizontalFlip(),
                     C.RandomVerticalFlip(),
                     C.RandomColorAdjust(),
                     C.RandomRotation(degrees=45)]

    try:
        _ = C.UniformAugment(operations=transforms_ua, num_ops=num_ops)

    except Exception as e:
        logger.info("Got an exception in DE: {}".format(str(e)))
        assert "num_ops" in str(e)


def test_cpp_uniform_augment_exception_nonpositive_numops(num_ops=0):
    """
    Test UniformAugment invalid non-positive number of ops
    """
    logger.info("Test CPP UniformAugment invalid non-positive num_ops exception")

    transforms_ua = [C.RandomCrop(size=[224, 224], padding=[32, 32, 32, 32]),
                     C.RandomHorizontalFlip(),
                     C.RandomVerticalFlip(),
                     C.RandomColorAdjust(),
                     C.RandomRotation(degrees=45)]

    try:
        _ = C.UniformAugment(operations=transforms_ua, num_ops=num_ops)

    except Exception as e:
        logger.info("Got an exception in DE: {}".format(str(e)))
        assert "num_ops" in str(e)

def test_cpp_uniform_augment_exception_float_numops(num_ops=2.5):
    """
    Test UniformAugment invalid float number of ops
    """
    logger.info("Test CPP UniformAugment invalid float num_ops exception")

    transforms_ua = [C.RandomCrop(size=[224, 224], padding=[32, 32, 32, 32]),
                     C.RandomHorizontalFlip(),
                     C.RandomVerticalFlip(),
                     C.RandomColorAdjust(),
                     C.RandomRotation(degrees=45)]

    try:
        _ = C.UniformAugment(operations=transforms_ua, num_ops=num_ops)

    except Exception as e:
        logger.info("Got an exception in DE: {}".format(str(e)))
        assert "integer" in str(e)

def test_cpp_uniform_augment_random_crop_badinput(num_ops=1):
    """
    Test UniformAugment with greater crop size
    """
    logger.info("Test CPP UniformAugment with random_crop bad input")
    batch_size = 2
    cifar10_dir = "../data/dataset/testCifar10Data"
    ds1 = de.Cifar10Dataset(cifar10_dir, shuffle=False)  # shape = [32,32,3]

    transforms_ua = [
        # Note: crop size [224, 224] > image size [32, 32]
        C.RandomCrop(size=[224, 224]),
        C.RandomHorizontalFlip()
    ]
    uni_aug = C.UniformAugment(operations=transforms_ua, num_ops=num_ops)
    ds1 = ds1.map(input_columns="image", operations=uni_aug)

    # apply DatasetOps
    ds1 = ds1.batch(batch_size, drop_remainder=True, num_parallel_workers=1)
    num_batches = 0
    try:
        for _ in ds1.create_dict_iterator():
            num_batches += 1
    except Exception as e:
        assert "Crop size" in str(e)


if __name__ == "__main__":
    test_uniform_augment(num_ops=1)
    test_cpp_uniform_augment(num_ops=1)
    test_cpp_uniform_augment_exception_pyops(num_ops=1)
    test_cpp_uniform_augment_exception_large_numops(num_ops=6)
    test_cpp_uniform_augment_exception_nonpositive_numops(num_ops=0)
    test_cpp_uniform_augment_exception_float_numops(num_ops=2.5)
    test_cpp_uniform_augment_random_crop_badinput(num_ops=1)
