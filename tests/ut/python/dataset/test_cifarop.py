# Copyright 2019 Huawei Technologies Co., Ltd
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
import mindspore.dataset as ds
from mindspore import log as logger

# Data for CIFAR and MNIST are not part of build tree
# They need to be downloaded directly
# prep_data.py can be executed or code below
# import sys
# sys.path.insert(0,"../../data")
# import prep_data
# prep_data.download_all_for_test("../../data")
DATA_DIR_10 = "../data/dataset/testCifar10Data"
DATA_DIR_100 = "../data/dataset/testCifar100Data"


def test_case_dataset_cifar10():
    """
    dataset parameter
    """
    logger.info("Test dataset parameter")
    # apply dataset operations
    data1 = ds.Cifar10Dataset(DATA_DIR_10, 100)

    num_iter = 0
    for _ in data1.create_dict_iterator():
        # in this example, each dictionary has keys "image" and "label"
        num_iter += 1
    assert num_iter == 100


def test_case_dataset_cifar100():
    """
    dataset parameter
    """
    logger.info("Test dataset parameter")
    # apply dataset operations
    data1 = ds.Cifar100Dataset(DATA_DIR_100, 100)

    num_iter = 0
    for _ in data1.create_dict_iterator():
        # in this example, each dictionary has keys "image" and "label"
        num_iter += 1
    assert num_iter == 100


if __name__ == '__main__':
    test_case_dataset_cifar10()
    test_case_dataset_cifar100()
