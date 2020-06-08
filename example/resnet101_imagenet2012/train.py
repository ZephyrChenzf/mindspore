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
# ============================================================================
"""train_imagenet."""
import os
import argparse
import random
import numpy as np
from dataset import create_dataset
from lr_generator import warmup_cosine_annealing_lr
from config import config
from mindspore import context
from mindspore import Tensor
from mindspore.model_zoo.resnet import resnet101
from mindspore.parallel._auto_parallel_context import auto_parallel_context
from mindspore.nn.optim.momentum import Momentum
from mindspore.train.model import Model, ParallelMode
from mindspore.train.callback import ModelCheckpoint, CheckpointConfig, LossMonitor, TimeMonitor
from mindspore.train.loss_scale_manager import FixedLossScaleManager
from mindspore.train.serialization import load_checkpoint, load_param_into_net
import mindspore.dataset.engine as de
from mindspore.communication.management import init
import mindspore.nn as nn
import mindspore.common.initializer as weight_init
from crossentropy import CrossEntropy

random.seed(1)
np.random.seed(1)
de.config.set_seed(1)

parser = argparse.ArgumentParser(description='Image classification')
parser.add_argument('--run_distribute', type=bool, default=False, help='Run distribute')
parser.add_argument('--device_num', type=int, default=1, help='Device num.')
parser.add_argument('--do_train', type=bool, default=True, help='Do train or not.')
parser.add_argument('--do_eval', type=bool, default=False, help='Do eval or not.')
parser.add_argument('--dataset_path', type=str, default=None, help='Dataset path')
parser.add_argument('--pre_trained', type=str, default=None, help='Pretrained checkpoint path')
args_opt = parser.parse_args()

device_id = int(os.getenv('DEVICE_ID'))

context.set_context(mode=context.GRAPH_MODE, device_target="Ascend", save_graphs=False, device_id=device_id,
                    enable_auto_mixed_precision=True)

if __name__ == '__main__':
    if not args_opt.do_eval and args_opt.run_distribute:
        context.set_auto_parallel_context(device_num=args_opt.device_num, parallel_mode=ParallelMode.DATA_PARALLEL,
                                          mirror_mean=True, parameter_broadcast=True)
        auto_parallel_context().set_all_reduce_fusion_split_indices([180, 313])
        init()

    epoch_size = config.epoch_size
    net = resnet101(class_num=config.class_num)
    # weight init
    for _, cell in net.cells_and_names():
        if isinstance(cell, nn.Conv2d):
            cell.weight.default_input = weight_init.initializer(weight_init.XavierUniform(),
                                                                cell.weight.default_input.shape(),
                                                                cell.weight.default_input.dtype()).to_tensor()
        if isinstance(cell, nn.Dense):
            cell.weight.default_input = weight_init.initializer(weight_init.TruncatedNormal(),
                                                                cell.weight.default_input.shape(),
                                                                cell.weight.default_input.dtype()).to_tensor()
    if not config.label_smooth:
        config.label_smooth_factor = 0.0
    loss = CrossEntropy(smooth_factor=config.label_smooth_factor, num_classes=config.class_num)
    if args_opt.do_train:
        dataset = create_dataset(dataset_path=args_opt.dataset_path, do_train=True,
                                 repeat_num=epoch_size, batch_size=config.batch_size)
        step_size = dataset.get_dataset_size()
        loss_scale = FixedLossScaleManager(config.loss_scale, drop_overflow_update=False)
        if args_opt.pre_trained:
            param_dict = load_checkpoint(args_opt.pre_trained)
            load_param_into_net(net, param_dict)

        # learning rate strategy with cosine
        lr = Tensor(warmup_cosine_annealing_lr(config.lr, step_size, config.warmup_epochs, 120,
                                               config.pretrain_epoch_size*step_size))
        opt = Momentum(filter(lambda x: x.requires_grad, net.get_parameters()), lr, config.momentum,
                       config.weight_decay, config.loss_scale)
        model = Model(net, loss_fn=loss, optimizer=opt, amp_level='O2', keep_batchnorm_fp32=False,
                      loss_scale_manager=loss_scale, metrics={'acc'})
        time_cb = TimeMonitor(data_size=step_size)
        loss_cb = LossMonitor()
        cb = [time_cb, loss_cb]
        if config.save_checkpoint:
            config_ck = CheckpointConfig(save_checkpoint_steps=config.save_checkpoint_epochs*step_size,
                                         keep_checkpoint_max=config.keep_checkpoint_max)
            ckpt_cb = ModelCheckpoint(prefix="resnet", directory=config.save_checkpoint_path, config=config_ck)
            cb += [ckpt_cb]
        model.train(epoch_size, dataset, callbacks=cb)
