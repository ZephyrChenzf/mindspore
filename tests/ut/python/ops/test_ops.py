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
""" test ops """
import functools

import numpy as np

import mindspore.nn as nn
import mindspore.ops.composite as C
from mindspore import Tensor
from mindspore import ops, Parameter, context
from mindspore.common import dtype as mstype
from mindspore.ops import functional as F
from mindspore.ops import operations as P
from mindspore.ops.operations import _grad_ops as G
from ..ut_filter import non_graph_engine
from ....mindspore_test_framework.mindspore_test import mindspore_test
from ....mindspore_test_framework.pipeline.forward.compile_forward \
    import (pipeline_for_compile_forward_ge_graph_for_case_by_case_config,
            pipeline_for_compile_forward_ge_graph_for_case_by_case_config_exception)
from ....mindspore_test_framework.pipeline.gradient.compile_gradient \
    import pipeline_for_compile_grad_ge_graph_for_case_by_case_config


class InputBackward(nn.Cell):
    def __init__(self, network):
        super(InputBackward, self).__init__()
        self.network = network
        self.network.set_train()
        self.grad = C.grad_all_with_sens

    def construct(self, x1, x2, x3, sens):
        return self.grad(self.network)(x1, x2, x3, sens)


class NetForTupleInput(nn.Cell):
    def __init__(self, op):
        super(NetForTupleInput, self).__init__()
        self.op = op

    def construct(self, x1, x2):
        return self.op((x1, x2))


class StridedSlicessdNet(nn.Cell):
    def __init__(self):
        super(StridedSlicessdNet, self).__init__()
        self.rank = P.Rank()

    def construct(self, x1):
        return P.StridedSlice(1, 1, 0, self.rank(x1), 0)(x1, (0, 0), (0, 0), (1, 1))


class NetForConcat(nn.Cell):
    def __init__(self):
        super(NetForConcat, self).__init__()
        self.concat = P.Concat()

    def construct(self, x1):
        return self.concat((x1, x1))


class NetForConcat1(nn.Cell):
    def __init__(self):
        super(NetForConcat1, self).__init__()
        self.concat = P.Concat()

    def construct(self, x1, x2):
        return self.concat((x1, x2))


class NetForPackInput(nn.Cell):
    def __init__(self, op):
        super(NetForPackInput, self).__init__()
        self.op = op
        self.mul = P.Mul()

    def construct(self, *args):
        t = ()
        for element in args:
            t = t + (self.mul(element, element),)
        return self.op(t)


class NetForUnpackInput(nn.Cell):
    def __init__(self, op):
        super(NetForUnpackInput, self).__init__()
        self.op = op
        self.mul = P.Mul()

    def construct(self, x1):
        return self.op((self.mul(x1, x1)))


class NetForFlatten(nn.Cell):
    def __init__(self):
        super(NetForFlatten, self).__init__()
        self.flatten = P.Flatten()

    def construct(self, x, y):
        return self.flatten(x) + y


class NetForFlatten0D(nn.Cell):
    def __init__(self):
        super(NetForFlatten0D, self).__init__()
        self.flatten = P.Flatten()

    def construct(self, x):
        return self.flatten(x)


class NetForFlattenComposed(nn.Cell):
    # make flatten op together with other ops for testing flatten grad
    def __init__(self):
        super(NetForFlattenComposed, self).__init__()
        self.flatten = P.Flatten()

    def construct(self, x, y):
        return self.flatten(x + x) + y


class ArgmaxNet(nn.Cell):
    def __init__(self):
        super(ArgmaxNet, self).__init__()
        self.argmax = P.Argmax(axis=1)

    def construct(self, input_):
        return self.argmax(input_)


class ArgminNet(nn.Cell):
    def __init__(self):
        super(ArgminNet, self).__init__()
        self.argmin = P.Argmin(axis=1)

    def construct(self, input_):
        return self.argmin(input_)


class CumSumNet(nn.Cell):
    def __init__(self):
        super(CumSumNet, self).__init__()
        self.cumsum = P.CumSum()
        self.axis = 1

    def construct(self, input_):
        return self.cumsum(input_, self.axis)


class SummaryNet(nn.Cell):
    def __init__(self):
        super(SummaryNet, self).__init__()
        self.s = P.ScalarSummary()
        self.add = P.TensorAdd()

    def construct(self, x, y):
        self.s("x1", x)
        return self.add(x, y)


class HistogramSummaryNet(nn.Cell):
    def __init__(self):
        super(HistogramSummaryNet, self).__init__()
        self.summary = P.HistogramSummary()
        self.add = P.TensorAdd()

    def construct(self, x, y):
        out = self.add(x, y)
        string_in = "out"
        self.summary(string_in, out)
        return out


class ScatterMax(nn.Cell):
    """ScatterMax net definition"""

    def __init__(self):
        super(ScatterMax, self).__init__()
        self.scatter_max = P.ScatterMax()
        self.ref = Parameter(Tensor(np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], np.float32)), name="ref")

    def construct(self, indices, updates):
        out = self.scatter_max(self.ref, indices, updates)
        return out


class ScatterAdd(nn.Cell):
    """ScatterAdd net definition"""

    def __init__(self, ref_shape):
        super(ScatterAdd, self).__init__()
        self.scatter_add = P.ScatterAdd()
        self.ref = Parameter(Tensor(np.ones(ref_shape, np.float32)), name="ref")

    def construct(self, indices, updates):
        out = self.scatter_add(self.ref, indices, updates)
        return out


class ApplyFtrlNet(nn.Cell):
    def __init__(self):
        super(ApplyFtrlNet, self).__init__()
        self.apply_ftrl = P.ApplyFtrl()
        self.lr = 0.001
        self.l1 = 0.0
        self.l2 = 0.0
        self.lr_power = -0.5
        self.var = Parameter(Tensor(np.random.rand(3, 3).astype(np.float32)), name="var")
        self.accum = Parameter(Tensor(np.random.rand(3, 3).astype(np.float32)), name="accum")
        self.linear = Parameter(Tensor(np.random.rand(3, 3).astype(np.float32)), name="linear")

    def construct(self, grad):
        out = self.apply_ftrl(self.var, self.accum, self.linear, grad, self.lr, self.l1, self.l2, self.lr_power)
        return out


class SparseApplyFtrlNet(nn.Cell):
    def __init__(self):
        super(SparseApplyFtrlNet, self).__init__()
        self.sparse_apply_ftrl = P.SparseApplyFtrl(lr=0.001, l1=0.0, l2=0.0, lr_power=-0.5)
        self.var = Parameter(Tensor(np.random.rand(3, 3).astype(np.float32)), name="var")
        self.accum = Parameter(Tensor(np.random.rand(3, 3).astype(np.float32)), name="accum")
        self.linear = Parameter(Tensor(np.random.rand(3, 3).astype(np.float32)), name="linear")

    def construct(self, grad, indices):
        out = self.sparse_apply_ftrl(self.var, self.accum, self.linear, grad, indices)
        return out


class SparseApplyProximalAdagradNet(nn.Cell):
    def __init__(self):
        super(SparseApplyProximalAdagradNet, self).__init__()
        self.sparse_apply_proximal_adagrad = P.SparseApplyProximalAdagrad()
        self.lr = 0.01
        self.l1 = 0.0
        self.l2 = 0.0

    def construct(self, var, accum, grad, indices):
        out = self.sparse_apply_proximal_adagrad(var, accum, self.lr, self.l1, self.l2, grad, indices)
        return out


class ApplyProximalAdagradNet(nn.Cell):
    def __init__(self):
        super(ApplyProximalAdagradNet, self).__init__()
        self.apply_proximal_adagrad = P.ApplyProximalAdagrad()
        self.lr = 0.01
        self.l1 = 0.0
        self.l2 = 0.0

    def construct(self, var, accum, grad):
        out = self.apply_proximal_adagrad(var, accum, self.lr, self.l1, self.l2, grad)
        return out


class ApplyRMSNet(nn.Cell):
    def __init__(self):
        super(ApplyRMSNet, self).__init__()
        self.apply_rms = P.ApplyRMSProp()
        self.lr = 0.001
        self.rho = 0.0
        self.momentum = 0.0
        self.epsilon = 1e-10
        self.var = Parameter(Tensor(np.random.rand(3, 3).astype(np.float32)), name="var")
        self.ms = Parameter(Tensor(np.random.rand(3, 3).astype(np.float32)), name="ms")
        self.moment = Parameter(Tensor(np.random.rand(3, 3).astype(np.float32)), name="moment")

    def construct(self, grad):
        out = self.apply_rms(self.var, self.ms, self.moment, self.lr, grad, self.rho, self.momentum, self.epsilon)
        return out


test_case_math_ops = [
    ('BitwiseAnd', {
        'block': P.BitwiseAnd(),
        'desc_inputs': [Tensor(np.array([0, 0, 1, -1, 1, 1, 1]), mstype.int16),
                        Tensor(np.array([0, 1, 1, -1, -1, 2, 3]), mstype.int16)],
        'skip': ['backward']}),
    ('BitwiseAnd_1', {
        'block': P.BitwiseAnd(),
        'desc_inputs': [Tensor(np.array([[1, 2, 3], [-1, -2, -3]]), mstype.int16),
                        Tensor(np.array([1, 1, 1]), mstype.int16)],
        'skip': ['backward']}),
    ('BitwiseOr', {
        'block': P.BitwiseOr(),
        'desc_inputs': [Tensor(np.array([0, 0, 1, -1, 1, 1, 1]), mstype.int16),
                        Tensor(np.array([0, 1, 1, -1, -1, 2, 3]), mstype.int16)],
        'skip': ['backward']}),
    ('BitwiseOr_1', {
        'block': P.BitwiseOr(),
        'desc_inputs': [Tensor(np.array([[1, 2, 3], [-1, -2, -3]]), mstype.int16),
                        Tensor(np.array([1, 1, 1]), mstype.int16)],
        'skip': ['backward']}),
    ('BitwiseXor', {
        'block': P.BitwiseXor(),
        'desc_inputs': [Tensor(np.array([0, 0, 1, -1, 1, 1, 1]), mstype.int16),
                        Tensor(np.array([0, 1, 1, -1, -1, 2, 3]), mstype.int16)],
        'skip': ['backward']}),
    ('BitwiseXor_1', {
        'block': P.BitwiseXor(),
        'desc_inputs': [Tensor(np.array([[1, 2, 3], [-1, -2, -3]]), mstype.int16),
                        Tensor(np.array([1, 1, 1]), mstype.int16)],
        'skip': ['backward']}),
    ('Neg', {
        'block': P.Neg(),
        'desc_inputs': [[1, 3, 4, 4]],
        'desc_bprop': [[1, 3, 4, 4]]}),
    ('Sub', {
        'block': P.Sub(),
        'desc_inputs': [[3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('TensorAdd', {
        'block': P.TensorAdd(),
        'desc_inputs': [[3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Mul0', {
        'block': P.Mul(),
        'desc_inputs': [[2, 3, 3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Mul1', {
        'block': P.Mul(),
        'desc_inputs': [[2, 3, 1, 1], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Mul2', {
        'block': P.Mul(),
        'desc_inputs': [[2, 3, 3, 5], [2, 3, 1, 1]],
        'desc_bprop': [[2, 3, 3, 5]],
        'skip': ['backward']}),
    ('Mul3', {
        'block': P.Mul(),
        'desc_inputs': [[3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]],
        'skip': ['backward']}),
    ('Mul4', {
        'block': P.Mul(),
        'desc_inputs': [[2, 3, 3, 5], [3, 5]],
        'desc_bprop': [[2, 3, 3, 5]],
        'skip': ['backward']}),
    ('Add0', {
        'block': P.TensorAdd(),
        'desc_inputs': [[2, 3, 3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Add1', {
        'block': P.TensorAdd(),
        'desc_inputs': [[3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]],
        'skip': ['backward']}),
    ('Add2', {
        'block': P.TensorAdd(),
        'desc_inputs': [[2, 3, 3, 5], [3, 5]],
        'desc_bprop': [[2, 3, 3, 5]],
        'skip': ['backward']}),
    ('Add3', {
        'block': P.TensorAdd(),
        'desc_inputs': [[2, 3, 1, 1], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]],
        'skip': ['backward']}),
    ('Add4', {
        'block': P.TensorAdd(),
        'desc_inputs': [[2, 3, 3, 5], [2, 3, 1, 1]],
        'desc_bprop': [[2, 3, 3, 5]],
        'skip': ['backward']}),
    ('Minimum', {
        'block': P.Minimum(),
        'desc_inputs': [[2, 3, 3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Pow_0', {
        'block': P.Pow(),
        'desc_const': [2.0],
        'desc_inputs': [[2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Pow_1', {
        'block': P.Pow(),
        'desc_inputs': [[3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Exp', {
        'block': P.Exp(),
        'desc_inputs': [[2, 3]],
        'desc_bprop': [[2, 3]]}),
    ('Expm1', {
        'block': P.Expm1(),
        'desc_inputs': [[2, 3]],
        'desc_bprop': [[2, 3]]}),
    ('Erf', {
        'block': P.Erf(),
        'desc_inputs': [Tensor(np.array([-2, -1, 0, 1, 2]).astype(np.float16))],
        'desc_bprop': [Tensor(np.array([-2, -1, 0, 1, 2]).astype(np.float16))]}),
    ('Floor', {
        'block': P.Floor(),
        'desc_inputs': [[2, 512, 56, 56]],
        'desc_bprop': [[2, 512, 56, 56]],
        'skip': ['backward']}),
    ('Ceil', {
        'block': P.Ceil(),
        'desc_inputs': [[2, 512, 56, 56]],
        'desc_bprop': [[2, 512, 56, 56]],
        'skip': ['backward']}),
    ('ACos', {
        'block': P.ACos(),
        'desc_inputs': [Tensor(np.array([2., 3.]).astype(np.float32))],
        'desc_bprop': [Tensor(np.array([2., 3.]).astype(np.float32))]}),
    ('ACosGrad', {
        'block': G.ACosGrad(),
        'desc_inputs': [[2, 3], [2, 3]],
        'skip': ['backward']}),
    ('Acosh', {
        'block': P.Acosh(),
        'desc_inputs': [Tensor(np.array([2., 3.]).astype(np.float32))],
        'desc_bprop': [Tensor(np.array([2., 3.]).astype(np.float32))]}),
    ('AcoshGrad', {
        'block': G.AcoshGrad(),
        'desc_inputs': [[2, 3], [2, 3]],
        'skip': ['backward']}),
    ('Sin', {
        'block': P.Sin(),
        'desc_inputs': [[2, 3]],
        'desc_bprop': [[2, 3]]}),
    ('Asin', {
        'block': P.Asin(),
        'desc_inputs': [[2, 3]],
        'desc_bprop': [[2, 3]]}),
    ('Asinh', {
        'block': P.Asinh(),
        'desc_inputs': [[3, 4, 5]],
        'desc_bprop': [[3, 4, 5]]}),
    ('Reciprocal', {
        'block': P.Reciprocal(),
        'desc_inputs': [[2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Minimum_0', {
        'block': P.Minimum(),
        'desc_inputs': [[2, 3, 3, 5], [3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Maximum', {
        'block': P.Maximum(),
        'desc_inputs': [[2, 3, 3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Maximum_0', {
        'block': P.Maximum(),
        'desc_inputs': [[3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('MaximumGrad', {
        'block': G.MaximumGrad(),
        'desc_inputs': [[2, 3, 3, 5], [2, 3, 3, 5], [2, 3, 3, 5]],
        'skip': ['backward']}),
    ('MinimumGrad', {
        'block': G.MinimumGrad(),
        'desc_inputs': [[2, 3, 3, 5], [2, 3, 3, 5], [2, 3, 3, 5]],
        'skip': ['backward']}),
    ('StridedSlice', {
        'block': P.StridedSlice(),
        'desc_const': [(0, 1, 2, 1),
                       (2, 3, 3, 4),
                       (1, 1, 1, 1)],
        'desc_inputs': [[2, 3, 3, 5]],
        'desc_bprop': [[2, 2, 1, 3]]}),
    ('Slice_1', {
        'block': P.Slice(),
        'desc_const': [(0, 1, 2, 1),
                       (1, 1, 1, 2)],
        'desc_inputs': [[2, 3, 3, 5]],
        'desc_bprop': [[1, 1, 1, 2]]}),
    ('StridedSliceGrad', {
        'block': G.StridedSliceGrad(),
        'desc_const': [(64, 1, 1024),
                       (0, 1, 0),
                       (64, 2, 1024),
                       (1, 1, 1)],
        'desc_inputs': [[64, 128, 1024]],
        'skip': ['backward']}),
    ('RandomChoiceWithMask', {
        'block': P.RandomChoiceWithMask(256),
        'desc_inputs': [Tensor(np.random.rand(24000, 4).astype(np.bool_))],
        'desc_bprop': [[256, 4], [256, 4]],
        'skip': ['backward']}),
    ('LessEqual', {
        'block': P.LessEqual(),
        'desc_inputs': [Tensor(np.random.rand(4).astype(np.float16)),
                        Tensor(np.random.rand(4).astype(np.float16))],
        'skip': ['backward']}),
    ('Less', {
        'block': P.Less(),
        'desc_inputs': [[2, 1, 4, 5], [2, 1, 4, 5]],
        'desc_bprop': [Tensor(np.zeros((2, 1, 4, 5), np.bool_))],
        'skip': ['backward']}),
    ('RealDiv_0', {
        'block': P.RealDiv(),
        'desc_const': [Tensor(2048.0), Tensor(0.0)],
        'desc_inputs': [],
        'skip': ['backward']}),
    ('RealDiv', {
        'block': P.RealDiv(),
        'desc_inputs': [[4], Tensor(np.ones(4).astype(np.float32))],
        'desc_bprop': [[4]]}),
    ('RealDiv_1', {
        'block': P.RealDiv(),
        'desc_inputs': [[512, 1024], [512, 1024]],
        'desc_bprop': [[512, 1024]]}),
    ('FloorDiv', {
        'block': P.FloorDiv(),
        'desc_inputs': [Tensor(np.random.rand(4).astype(np.float16)),
                        Tensor(np.random.rand(4).astype(np.float16))],
        'skip': ['backward']}),
    ('FloorMod', {
        'block': P.FloorMod(),
        'desc_inputs': [[3, 4, 5], [2, 3, 4, 5]],
        'desc_bprop': [[2, 3, 4, 5]]}),
    ('identity', {
        'block': ops.functional.identity,
        'desc_inputs': [[2, 2]],
        'skip': ['backward']}),
    ('MatMul_1', {
        'block': P.MatMul(transpose_a=False, transpose_b=False),
        'desc_inputs': [[1024, 160], [160, 1024]],
        'desc_bprop': [[1024, 1024]]}),
    ('MatMul_2', {
        'block': P.MatMul(transpose_a=True, transpose_b=True),
        'desc_inputs': [[160, 1024], [1024, 160]],
        'desc_bprop': [[1024, 1024]]}),
    ('Sub', {
        'block': P.Sub(),
        'desc_inputs': [[3], [3]],
        'desc_bprop': [[3]]}),
    ('TruncatedNormal', {
        'block': P.TruncatedNormal(),
        'desc_const': [(1, 2, 3)],
        'desc_inputs': [],
        'skip': ['backward'],
        'add_fake_input': True}),
    ('Select', {
        'block': P.Select(),
        'desc_inputs': [Tensor(np.array([[True, False, False], [False, True, True]])),
                        [2, 3], [2, 3]],
        'desc_bprop': [[2, 3]]}),
    ('Rank', {
        'block': P.Rank(),
        'desc_inputs': [[2, 3]],
        'skip': ['backward']}),
    ('InvertPermutation', {
        'block': P.InvertPermutation(),
        'desc_const': [(0, 3, 1, 2)],
        'desc_inputs': [],
        'skip': ['backward']}),
    ('Square', {
        'block': P.Square(),
        'desc_inputs': [[4]],
        'desc_bprop': [[4]]}),
    ('Rsqrt', {
        'block': P.Rsqrt(),
        'desc_inputs': [[4]],
        'desc_bprop': [[4]]}),
    ('Sqrt', {
        'block': P.Sqrt(),
        'desc_inputs': [[4]],
        'desc_bprop': [[4]]}),
    ('RealDiv', {
        'block': P.RealDiv(),
        'desc_inputs': [[4, 5], [2, 3, 4, 5]],
        'desc_bprop': [[2, 3, 4, 5]]}),
    ('Div', {
        'block': P.Div(),
        'desc_inputs': [[4, 5], [2, 3, 4, 5]],
        'desc_bprop': [[2, 3, 4, 5]]}),
    ('Equal', {
        'block': P.Equal(),
        'desc_inputs': [[3, 4, 5], [4, 5]],
        'desc_bprop': [Tensor(np.zeros((3, 4, 5), np.bool_))]}),
    ('NotEqual', {
        'block': P.NotEqual(),
        'desc_inputs': [[4, 1], [2, 3, 4, 5]],
        'desc_bprop': [Tensor(np.ones((2, 3, 4, 5), np.bool_))]}),
    ('NotEqual_0', {
        'block': P.NotEqual(),
        'desc_inputs': [1, [2, 3, 4, 5]],
        'desc_bprop': [Tensor(np.ones((2, 3, 4, 5), np.bool_))],
        'skip': ['backward']}),
    ('Greater', {
        'block': P.Greater(),
        'desc_inputs': [[2, 3, 4, 1], [4, 5]],
        'desc_bprop': [Tensor(np.ones((2, 3, 4, 5), np.bool_))]}),
    ('GreaterEqual', {
        'block': P.GreaterEqual(),
        'desc_inputs': [[2, 3, 4, 1], [4, 5]],
        'desc_bprop': [Tensor(np.ones((2, 3, 4, 5), np.bool_))]}),
    ('LogicalNot', {
        'block': P.LogicalNot(),
        'desc_inputs': [Tensor(np.zeros((3, 4, 5), np.bool_))],
        'desc_bprop': [Tensor(np.ones((3, 4, 5), np.bool_))]}),
    ('LogicalAnd', {
        'block': P.LogicalAnd(),
        'desc_inputs': [Tensor(np.zeros((2, 3, 4), np.bool_)), Tensor(np.ones((1), np.bool_))],
        'desc_bprop': [Tensor(np.zeros((2, 3, 4), np.bool_))]}),
    ('LogicalOr', {
        'block': P.LogicalOr(),
        'desc_inputs': [Tensor(np.zeros((3, 4, 5), np.bool_)), Tensor(np.ones((3, 1, 1), np.bool_))],
        'desc_bprop': [Tensor(np.zeros((3, 4, 5), np.bool_))]}),
    ('NpuAllocFloatStatus', {
        'block': P.NPUAllocFloatStatus(),
        'desc_inputs': [],
        'add_fack_input': True,
        'fack_input_type': np.float32,
        'desc_bprop': [Tensor(np.zeros([8]).astype(np.float32))],
        'skip': ['backward']}),
    ('NpuGetFloatStatus', {
        'block': P.NPUGetFloatStatus(),
        'desc_inputs': [Tensor(np.zeros([8]).astype(np.float32))],
        'desc_bprop': [Tensor(np.zeros([8]).astype(np.float32))],
        'skip': ['backward']}),
    ('NpuClearFloatStatus', {
        'block': P.NPUClearFloatStatus(),
        'desc_inputs': [Tensor(np.zeros([8]).astype(np.float32))],
        'desc_bprop': [Tensor(np.zeros([8]).astype(np.float32))],
        'skip': ['backward']}),
    ('CheckValid', {
        'block': P.CheckValid(),
        'desc_inputs': [[20000, 4], [3]],
        'desc_bprop': [[20000]],
        'skip': ['backward']}),
    ('NMSWithMask', {
        'block': P.NMSWithMask(0.5),
        'desc_inputs': [[128, 5]],
        'desc_bprop': [[128, 5], [128], [128]],
        'skip': ['backward']}),
    ('Abs', {
        'block': P.Abs(),
        'desc_inputs': [[4]],
        'desc_bprop': [[4]]}),
    ('CumSum', {
        'block': CumSumNet(),
        'desc_inputs': [Tensor(np.array([[3, 4, 6, 10], [1, 6, 7, 9], [4, 3, 8, 7], [1, 3, 7, 9]]).astype(np.float32))],
        'desc_bprop': [Tensor(np.array([[3, 4, 6, 10], [1, 6, 7, 9], [4, 3, 8, 7],
                                        [1, 3, 7, 9]]).astype(np.float32))]}),
    ('ReduceSum_3', {
        'block': P.ReduceSum(),
        'desc_const': [0],
        'desc_inputs': [[3, 2]],
        'desc_bprop': [[2]]}),
    ('ReduceSum_4', {
        'block': P.ReduceSum(keep_dims=True),
        'desc_const': [0],
        'desc_inputs': [[3, 2]],
        'desc_bprop': [[1, 2]]}),
    ('ReduceSum_5', {
        'block': P.ReduceSum(keep_dims=True),
        'desc_inputs': [[2, 3, 4]],
        'desc_bprop': [[1, 1, 1]]}),
    ('ReduceSum_6', {
        'block': P.ReduceSum(),
        'desc_inputs': [[2, 3, 4]],
        'desc_bprop': [[1]]}),
    ('Sum_0', {
        'block': P.ReduceSum(),
        'desc_const': [(1,)],
        'desc_inputs': [[3, 2]],
        'desc_bprop': [[3]]}),
    ('Sum_1', {
        'block': P.ReduceSum(keep_dims=True),
        'desc_const': [(1,)],
        'desc_inputs': [[3, 2]],
        'desc_bprop': [[3, 1]]}),
    ('Sum_2', {
        'block': P.ReduceSum(),
        'desc_const': [(0, 1)],
        'desc_inputs': [[3, 2]],
        'desc_bprop': [[1]]}),
    ('Sum_3', {
        'block': P.ReduceSum(),
        'desc_const': [0],
        'desc_inputs': [[3, 2]],
        'desc_bprop': [[2]]}),
    ('Sum_4', {
        'block': P.ReduceSum(keep_dims=True),
        'desc_const': [0],
        'desc_inputs': [[3, 2]],
        'desc_bprop': [[1, 2]]}),
    ('Sum_5', {
        'block': P.ReduceSum(keep_dims=True),
        'desc_const': [()],
        'desc_inputs': [[2, 3, 4]],
        'desc_bprop': [[1, 1, 1]]}),
    ('Sum_6', {
        'block': P.ReduceSum(),
        'desc_const': [()],
        'desc_inputs': [[2, 3, 4]],
        'desc_bprop': [[1]]}),
    ('Sign', {
        'block': P.Sign(),
        'desc_inputs': [[3]],
        'desc_bprop': [[3]]}),
    ('Round', {
        'block': P.Round(),
        'desc_inputs': [[3]],
        'desc_bprop': [[3]]}),
    ('Atan2', {
        'block': P.Atan2(),
        'desc_inputs': [Tensor(np.array([0, 1]).astype(np.float32)),
                        Tensor(np.array([1, 1]).astype(np.float32))],
        'desc_bprop': [[2]]}),
    ('SquareSumAll', {
        'block': P.SquareSumAll(),
        'desc_inputs': [Tensor(np.array([0, 1, 4, 5]).astype(np.float32)),
                        Tensor(np.array([1, 1, 3, 7]).astype(np.float32))],
        'skip': ['backward']}),
    ('Cos', {
        'block': P.Cos(),
        'desc_inputs': [[2, 3]],
        'desc_bprop': [[2, 3]]}),
    ('ReduceAll', {
        'block': P.ReduceAll(),
        'desc_const': [1],
        'desc_inputs': [Tensor(np.array([[True, False], [True, True]]))],
        'desc_bprop': []}),
    ('BesselI0e', {
        'block': P.BesselI0e(),
        'desc_inputs': [[2, 3]],
        'desc_bprop': [[2, 3]]}),
    ('BesselI1e', {
        'block': P.BesselI1e(),
        'desc_inputs': [[2, 3]],
        'desc_bprop': [[2, 3]]}),
    ('Atan', {
        'block': P.Atan(),
        'desc_inputs': [[2, 3]],
        'desc_bprop': [[2, 3]]}),
    ('AtanGrad', {
        'block': G.AtanGrad(),
        'desc_inputs': [[2, 3], [2, 3]],
        'skip': ['backward']}),
    ('Atanh', {
        'block': P.Atanh(),
        'desc_inputs': [[2, 3]],
        'desc_bprop': [[2, 3]]}),
    ('Cosh', {
        'block': P.Cosh(),
        'desc_inputs': [[3, 4, 5]],
        'desc_bprop': [[3, 4, 5]]}),
    ('Sinh', {
        'block': P.Sinh(),
        'desc_inputs': [[3, 4, 5]],
        'desc_bprop': [[3, 4, 5]]}),
    ('Inv', {
        'block': P.Inv(),
        'desc_inputs': [[21, 9, 12, 5]],
        'desc_bprop': [[21, 9, 12, 5]]}),
    ('Invert', {
        'block': P.Invert(),
        'desc_inputs': [Tensor(np.array([[24, 4, 13, 9], [1, 5, 10, 8]]).astype(np.int16))],
        'desc_bprop': [],
        'skip': ['backward']}),
]

test_case_nn_ops = [
    ('BiasAdd', {
        'block': P.BiasAdd(),
        'desc_inputs': [[1, 3, 3, 3], [3]],
        'desc_bprop': [[1, 3, 3, 3]]}),
    ('BiasAddGrad', {
        'block': G.BiasAddGrad(),
        'desc_inputs': [[1, 3, 3, 3]],
        'skip': ['backward']}),
    ('Gelu', {
        'block': P.Gelu(),
        'desc_inputs': [[1, 3, 4, 4]],
        'desc_bprop': [[1, 3, 4, 4]]}),
    ('GeluGrad', {
        'block': G.GeluGrad(),
        'desc_inputs': [[2, 2], [2, 2], [2, 2]],
        'desc_bprop': [[2, 2]],
        'skip': ['backward']}),
    ('Tanh', {
        'block': P.Tanh(),
        'desc_inputs': [[1, 3, 4, 4]],
        'desc_bprop': [[1, 3, 4, 4]]}),
    ('TanhGrad', {
        'block': G.TanhGrad(),
        'desc_inputs': [[1, 3, 4, 4], [1, 3, 4, 4]],
        'desc_bprop': [[1, 3, 4, 4]],
        'skip': ['backward']}),
    ('ReLU', {
        'block': P.ReLU(),
        'desc_inputs': [[1, 3, 4, 4]],
        'desc_bprop': [[1, 3, 4, 4]]}),
    ('ReLU6', {
        'block': P.ReLU6(),
        'desc_inputs': [[1, 3, 4, 4]],
        'desc_bprop': [[1, 3, 4, 4]]}),
    ('ReLUV2', {
        'block': P.ReLUV2(),
        'desc_inputs': [[1, 3, 4, 4]],
        'desc_bprop': [[1, 3, 4, 4], ([1, 1, 4, 4, 2], {'dtype': np.uint8})]}),
    ('ReLUGrad', {
        'block': G.ReluGrad(),
        'desc_inputs': [[1, 3, 4, 4], [1, 3, 4, 4]],
        'skip': ['backward']}),
    ('Softplus', {
        'block': P.Softplus(),
        'desc_inputs': [[1, 3, 4, 4]],
        'desc_bprop': [[1, 3, 4, 4]]}),
    ('SoftplusGrad', {
        'block': G.SoftplusGrad(),
        'desc_inputs': [[1, 3, 4, 4], [1, 3, 4, 4]],
        'skip': ['backward']}),
    ('Elu', {
        'block': P.Elu(),
        'desc_inputs': [[2, 3, 4]],
        'desc_bprop': [[2, 3, 4]]}),
    ('EluGrad', {
        'block': G.EluGrad(),
        'desc_inputs': [[2, 3, 4], [2, 3, 4]],
        'desc_bprop': [[2, 3, 4]],
        'skip': ['backward']}),
    ('Sigmoid', {
        'block': P.Sigmoid(),
        'desc_inputs': [[1, 3, 4, 4]],
        'desc_bprop': [[1, 3, 4, 4]]}),
    ('MaxPool', {
        'block': P.MaxPool(ksize=(2, 2), strides=(2, 2), padding="VALID"),
        'desc_inputs': [[100, 3, 28, 28]],
        'desc_bprop': [[100, 3, 14, 14]]}),
    ('MaxPoolGrad', {
        'block': G.MaxPoolGrad(ksize=(2, 2), strides=(2, 2), padding="VALID"),
        'desc_inputs': [[3, 4, 6, 6], [3, 4, 3, 3], [3, 4, 3, 3]],
        'desc_bprop': [[3, 4, 6, 6]],
        'skip': ['backward']}),
    ('AvgPool', {
        'block': P.AvgPool(ksize=(2, 2), strides=(2, 2), padding="VALID"),
        'desc_inputs': [[100, 3, 28, 28]],
        'desc_bprop': [[100, 3, 14, 14]]}),
    ('AvgPoolGrad', {
        'block': G.AvgPoolGrad(ksize=(2, 2), strides=(2, 2), padding="VALID"),
        'desc_const': [(3, 4, 6, 6)],
        'const_first': True,
        'desc_inputs': [[3, 4, 6, 6]],
        'desc_bprop': [[3, 4, 6, 6]],
        'skip': ['backward']}),
    ('MaxPoolWithArgmax', {
        'block': P.MaxPoolWithArgmax(ksize=2, strides=2),
        'desc_inputs': [[128, 32, 32, 64]],
        'desc_bprop': [[128, 32, 16, 32], ([128, 32, 4, 33], {'dtype': np.uint16})]}),
    ('SoftmaxCrossEntropyWithLogits', {
        'block': P.SoftmaxCrossEntropyWithLogits(),
        'desc_inputs': [[1, 10], [1, 10]],
        'desc_bprop': [[1], [1, 10]],
        'skip': ['backward_exec']}),
    ('Flatten', {
        'block': P.Flatten(),
        'desc_inputs': [[128, 32, 32, 64]],
        'desc_bprop': [[128, 65536]]}),
    ('LogSoftmax', {
        'block': P.LogSoftmax(),
        'desc_inputs': [[64, 2]],
        'desc_bprop': [[64, 2]]}),
    ('LogSoftmaxGrad', {
        'block': G.LogSoftmaxGrad(),
        'desc_inputs': [[16, 1234], [16, 1234]],
        'desc_bprop': [[64, 2]],
        'skip': ['backward']}),
    ('L2Normalize', {
        'block': P.L2Normalize(),
        'desc_inputs': [[2, 2]],
        'desc_bprop': [[2, 2]]}),
    ('L2NormalizeGrad', {
        'block': G.L2NormalizeGrad(),
        'desc_inputs': [[2, 2], [2, 2], [2, 2]],
        'desc_bprop': [[2, 2]],
        'skip': ['backward']}),
    ('LayerNorm', {
        'block': P.LayerNorm(),
        'desc_inputs': [[2, 16], [16], [16]],
        'desc_bprop': [[2, 16], [2, 1], [2, 1]]}),
    ('LayerNormGrad', {
        'block': G.LayerNormGrad(),
        'desc_inputs': [[2, 16], [2, 16], [2, 16], [2, 16], [16]],
        'desc_bprop': [[2, 16], [16], [16]],
        'skip': ['backward']}),
    ('FusedBatchNorm', {
        'block': P.FusedBatchNorm(),
        'desc_inputs': [[128, 64, 32, 64], [64], [64], [64], [64]],
        'desc_bprop': [[128, 64, 32, 64], [64], [64], [64], [64]],
        'skip': []}),
    ('FusedBatchNormGrad', {
        'block': G.FusedBatchNormGrad(),
        'desc_inputs': [[128, 64, 32, 64], [128, 64, 32, 64], [64], [64], [64]],
        'desc_bprop': [[128, 64, 32, 64], [64], [64], [64], [64]],
        'skip': ['backward']}),
    ('BatchNorm', {
        'block': P.BatchNorm(),
        'desc_inputs': [[128, 64, 32, 32], [64], [64], [64], [64]],
        'desc_bprop': [[128, 64, 32, 32], [64], [64], [64], [64]],
        'skip': []}),
    ('BatchNormGrad', {
        'block': G.BatchNormGrad(),
        'desc_inputs': [[128, 64, 32, 32], [128, 64, 32, 32], [64], [64], [64]],
        'desc_bprop': [[128, 64, 32, 32], [64], [64], [64], [64]],
        'skip': ['backward']}),
    ('BasicLSTMCell', {
        'block': P.BasicLSTMCell(keep_prob=1.0, forget_bias=1.0, state_is_tuple=True, activation='tanh'),
        'desc_inputs': [[128, 128], [128, 128], [128, 128], [512, 256, 1, 1], [512, 1, 1, 1]],
        'desc_bprop': [[128, 128], [128, 128], [128, 128], [128, 128], [128, 128], [128, 128], [128, 128]],
        'skip': []}),
    ('TopK', {
        'block': P.TopK(),
        'desc_const': [5],
        'desc_inputs': [[20, 20, 10]],
        'desc_bprop': [[20, 20, 5]],
        'skip': ['backward']}),
    ('GatherV2_0', {
        'block': P.GatherV2(),
        'desc_const': [0],
        'desc_inputs': [[3, 1, 2], Tensor(np.array([0, 1]).astype(np.int32))],
        'desc_bprop': [[2, 1, 2]]}),
    ('GatherV2_1', {
        'block': P.GatherV2(),
        'desc_const': [2],
        'desc_inputs': [[3, 1, 3], Tensor(np.array([0, 1]).astype(np.int32))],
        'desc_bprop': [[3, 1, 2]]}),
    ('GatherV2_2', {
        'block': P.GatherV2(),
        'desc_const': [0],
        'desc_inputs': [[3, 1, 3], Tensor(np.array([[0, 1], [0, 1], [0, 1]]).astype(np.int32))],
        'desc_bprop': [[3, 2, 1, 3]]}),
    ('GatherV2_3', {
        'block': P.GatherV2(),
        'desc_const': [2],
        'desc_inputs': [[3, 1, 3], Tensor(np.array([[0, 1], [0, 1], [0, 1]]).astype(np.int32))],
        'desc_bprop': [[3, 1, 3, 2]]}),
    ('GatherV2_4', {
        'block': P.GatherV2(),
        'desc_const': [1],
        'desc_inputs': [[32, 5, 1024], Tensor(np.array([3]).astype(np.int32))],
        'desc_bprop': [[32, 1, 1024]]}),
    ('GatherV2_5', {
        'block': P.GatherV2(),
        'desc_const': [-1],
        'desc_inputs': [[3, 1, 3], Tensor(np.array([0, 1]).astype(np.int32))],
        'desc_bprop': [[3, 1, 2]]}),
    ('GatherV2_6', {
        'block': P.GatherV2(),
        'desc_const': [0],
        'desc_inputs': [[1152], Tensor(np.array(10).astype(np.int32))],
        'desc_bprop': [Tensor(np.array(10).astype(np.float32))]}),
    ('Range', {
        'block': P.Range(1.0, 5.0),
        'desc_inputs': [Tensor(np.ones([10]).astype(np.float32))],
        'desc_bprop': [[10]]}),
    ('UnsortedSegmentSum', {
        'block': P.UnsortedSegmentSum(),
        'desc_const': [1280],
        'desc_inputs': [[1280, 1024], Tensor(np.ones(1280).astype(np.int32))],
        'desc_bprop': [[8192, 1024]],
        'skip': ['backward']}),
    ('UnsortedSegmentSum_1', {
        'block': P.UnsortedSegmentSum(),
        'desc_const': [4],
        'desc_inputs': [[3, 2, 1, 3], Tensor(np.array([[0, 1], [0, 1], [0, 1]]).astype(np.int32))],
        'desc_bprop': [[4, 1, 3]],
        'skip': ['backward']}),
    ('UnsortedSegmentMin', {
        'block': P.UnsortedSegmentMin(),
        'desc_const': [4],
        'desc_inputs': [[3, 2, 1, 3], Tensor(np.array([1, 2, 3]).astype(np.int32))],
        'desc_bprop': [[4, 2, 1, 3]]}),
    ('DropoutGenMask', {
        'block': P.DropoutGenMask(),
        'desc_const': [(2, 2), Tensor(0.5, mstype.float32)],
        'desc_inputs': [],
        'desc_bprop': [Tensor(np.ones(1).astype(np.int8))],
        'skip': ['backward']}),
    ('DropoutDoMask', {
        'block': P.DropoutDoMask(),
        'desc_const': [Tensor(0.5)],
        'desc_inputs': [[64, 12, 128, 128], Tensor(np.ones(1572864).astype(np.uint8))],
        'desc_bprop': [[64, 12, 128, 128]]}),
    ('Dropout', {
        'block': nn.Dropout(0.5),
        'desc_inputs': [[64, 12, 128, 128]],
        'desc_bprop': [[64, 12, 128, 128]]}),
    ('ReduceMean0', {
        'block': P.ReduceMean(),
        'desc_const': [(2,)],
        'desc_inputs': [[3, 2, 2]],
        'desc_bprop': [[3, 2]]}),
    ('ReduceMean1', {
        'block': P.ReduceMean(),
        'desc_const': [2],
        'desc_inputs': [[3, 2, 2]],
        'desc_bprop': [[3, 2]]}),
    ('All', {
        'block': P.ReduceAll(),
        'desc_const': [(1,)],
        'desc_inputs': [Tensor(np.ones([3, 2]).astype(np.bool_))],
        'desc_bprop': [[3]],
        'skip': ['backward']}),
    ('DescConst', {
        'block': Tensor(np.array([2], np.float32)),
        'desc_inputs': [],
        'desc_bprop': [[1]],
        'skip': ['backward'],
        'add_fake_input': True}),
    ('Fill', {
        'block': P.Fill(),
        'desc_const': [mstype.float32, (2, 3), 1.0],
        'desc_inputs': [],
        'desc_bprop': [[2, 3]],
        'skip': ['backward'],
        'add_fake_input': True}),
    ('OnesLike', {
        'block': P.OnesLike(),
        'desc_inputs': [Tensor(np.array([[0, 1], [2, 1]]).astype(np.int32))],
        'desc_bprop': [Tensor(np.array([[1, 1], [1, 1]]).astype(np.int32))]
    }),
    ('ZerosLike', {
        'block': P.ZerosLike(),
        'desc_inputs': [Tensor(np.array([[0, 1], [2, 1]]).astype(np.int32))],
        'desc_bprop': [Tensor(np.array([[1, 1], [1, 1]]).astype(np.int32))]
    }),
    ('Softmax', {
        'block': P.Softmax(),
        'desc_inputs': [[5, 5]],
        'desc_bprop': [[5, 5]]}),
    ('DepthwiseConv2dNative_1', {
        'block': P.DepthwiseConv2dNative(3, (3, 3), pad_mode="pad", pad=1, stride=2),
        'desc_inputs': [[10, 32, 32, 32], [1, 32, 3, 3]],
        'desc_bprop': [[10, 32, 16, 16]]}),
    ('DepthwiseConv2dNative_2', {
        'block': P.DepthwiseConv2dNative(1, (3, 3), pad_mode="same", pad=0, stride=1),
        'desc_inputs': [[2592, 2048, 4, 4], [1, 2048, 3, 3]],
        'desc_bprop': [[2592, 2048, 4, 4]]}),
    ('SigmoidCrossEntropyWithLogits', {
        'block': P.SigmoidCrossEntropyWithLogits(),
        'desc_inputs': [[128, 10], [128, 10]],
        'desc_bprop': [[128, 10]]}),
    ('Pad', {
        'block': P.Pad(((1, 2), (2, 3))),
        'desc_inputs': [[7, 7]],
        'desc_bprop': [[10, 12]]}),
    ('BinaryCrossEntropy', {
        'block': P.BinaryCrossEntropy(),
        'desc_inputs': [[1, 2, 3], [1, 2, 3], [1, 2, 3]],
        'desc_bprop': []}),
    ('SparseApplyAdagrad', {
        'block': P.SparseApplyAdagrad(0.5),
        'desc_inputs': [[3, 3], [3, 3], [3, 3], Tensor(np.ones((3,), np.int32))],
        'skip': ['backward']}),
    ('SparseApplyFtrl', {
        'block': SparseApplyFtrlNet(),
        'desc_inputs': [[3, 3], Tensor(np.ones((3,), np.int32))],
        'skip': ['backward']}),
    ('ApplyProximalAdagrad', {
        'block': ApplyProximalAdagradNet(),
        'desc_inputs': [[3, 3], [3, 3], [3, 3]],
        'skip': ['backward']}),
    ('SparseApplyProximalAdagrad', {
        'block': SparseApplyProximalAdagradNet(),
        'desc_inputs': [[3, 3], [3, 3], [3, 3], Tensor(np.ones((3,), np.int32))],
        'skip': ['backward']}),
    ('Flatten_1', {
        'block': NetForFlatten(),
        'desc_inputs': [Tensor(np.ones([2, 3, 4]).astype(np.int32)), Tensor(np.ones([2, 12]).astype(np.int32))],
        'desc_bprop': [Tensor(np.ones([2, 12]).astype(np.int32))],
        'skip': ['backward']}),
    ('Flatten_2', {
        'block': NetForFlatten(),
        'desc_inputs': [Tensor(np.ones([8]).astype(np.int32)), Tensor(np.ones([8, 3]).astype(np.int32))],
        'desc_bprop': [Tensor(np.ones([8, 3]).astype(np.int32))],
        'skip': ['backward']}),
    ('Flatten_3', {
        'block': NetForFlattenComposed(),
        'desc_inputs': [Tensor(np.ones([2, 3, 4]).astype(np.int32)), Tensor(np.ones([2, 12]).astype(np.int32))],
        'desc_bprop': [Tensor(np.ones([2, 12]).astype(np.int32))],
        'skip': []}),
    ('ArgmaxNet', {
        'block': ArgmaxNet(),
        'desc_inputs': [Tensor(np.array([[128, 32, 32, 64], [128, 32, 32, 64]]).astype(np.float16))],
        'desc_bprop': [Tensor(np.array([[128, 32, 32, 64], [128, 32, 32, 64]]).astype(np.float16))],
        'skip': ['backward']}),
    ('ArgminNet', {
        'block': ArgminNet(),
        'desc_inputs': [Tensor(np.array([[128, 32, 32, 64], [128, 32, 32, 64]]).astype(np.float16))],
        'desc_bprop': [Tensor(np.array([[128, 32, 32, 64], [128, 32, 32, 64]]).astype(np.float16))],
        'skip': ['backward']}),
    ('OneHot', {
        'block': P.OneHot(),
        'desc_const': [3, Tensor(1.0, mstype.float32), Tensor(0.0, mstype.float32)],
        'desc_inputs': [Tensor(np.array([64]).astype(np.int32))],
        'desc_bprop': [[1, 3]]}),
    ('ReduceProd_0', {
        'block': P.ReduceProd(),
        'desc_const': [0],
        'desc_inputs': [[3, 2]],
        'desc_bprop': [[2]]}),
    ('ReduceProd_1', {
        'block': P.ReduceProd(keep_dims=True),
        'desc_const': [0],
        'desc_inputs': [[3, 2]],
        'desc_bprop': [[1, 2]]}),
    ('CumProd', {
        'block': P.CumProd(),
        'desc_const': [0],
        'desc_inputs': [[3, 2]],
        'desc_bprop': [[3, 2]]}),
    ('ApplyFtrl', {
        'block': ApplyFtrlNet(),
        'desc_inputs': [[3, 3]],
        'desc_bprop': [3, 3],
        'skip': ['backward']}),
    ('ApplyRMSProp', {
        'block': ApplyRMSNet(),
        'desc_inputs': [[3, 3]],
        'desc_bprop': [3, 3],
        'skip': ['backward']}),
    ('ApplyCenteredRMSProp', {
        'block': P.ApplyCenteredRMSProp(),
        'desc_const': [0.9, 0.0, 1e-10, 0.001],
        'desc_inputs': [Tensor(1., mstype.float32), Tensor(2., mstype.float32), Tensor(1., mstype.float32),
                        Tensor(2., mstype.float32), Tensor(1., mstype.float32)],
        'desc_bprop': [1],
        'skip': ['backward']}),
    ('CTCLoss', {
        'block': P.CTCLoss(),
        'desc_inputs': [Tensor(np.ones([6, 4, 6]).astype(np.float32)),
                        Tensor(np.array([[0, 1], [1, 0], [2, 3], [3, 2]]).astype(np.int64)),
                        Tensor(np.array([1, 2, 3, 4]).astype(np.int32)),
                        Tensor(np.array([6, 6, 6, 6]).astype(np.int32))],
        'desc_bprop': [[4], [6, 4, 6]]}),
    ('L2Loss_1', {
        'block': P.L2Loss(),
        'desc_inputs': [Tensor(np.array([1, 2, 3, 4]), mstype.float32)],
        'desc_bprop': []}),
    ('L2Loss_2', {
        'block': P.L2Loss(),
        'desc_inputs': [Tensor(np.array([[1, 1], [2, 2], [3, 3], [4, 4]]), mstype.float16)],
        'desc_bprop': []}),
    ('ResizeBilinear', {
        'block': P.ResizeBilinear((5, 5)),
        'desc_inputs': [Tensor([[[[1, 2, 3, 4, 5], [1, 2, 3, 4, 5]]]], mstype.float16)],
        'desc_bprop': [Tensor([[[[1, 2, 3, 4, 5], [1, 2, 3, 4, 5]]]], mstype.float16)]}),
    ('ResizeBilinearGrad', {
        'block': G.ResizeBilinearGrad(),
        'desc_inputs': [Tensor([[[[1, 2, 3, 4, 5]]]], mstype.float32), Tensor([[[[1, 2, 3, 4, 5]]]], mstype.float32)],
        'desc_bprop': [Tensor([[[[1, 2, 3, 4, 5]]]], mstype.float32)],
        'skip': ['backward']}),
    ('ROIAlign', {
        'block': P.ROIAlign(7, 7, 0.03125, 2),
        'desc_inputs': [[2, 256, 192, 320], [1024, 5]],
        'desc_bprop': [[7, 7]]}),
    ('ROIAlignGrad', {
        'block': G.ROIAlignGrad((1, 1, 1, 1), 2, 2, 0.5, 2),
        'desc_inputs': [[1, 1, 2, 2], [1, 5]],
        'desc_bprop': [[1, 1, 2, 2]],
        'skip': ['backward']}),
    ('LARSUpdate', {
        'block': P.LARSUpdate(1e-05, 0.001, False),
        'desc_const': [0.0, 0.001],
        'desc_inputs': [[3, 3], [3, 3], [3, 3], [3, 3]],
        'desc_bprop': [3, 3],
        'skip': ['backward']}),
    ('SGD', {
        'block': P.SGD(0.0, 0.0, False),
        'desc_inputs': [[3, 3], [3, 3], Tensor(0.001, mstype.float32), [3, 3], Tensor(0.1, mstype.float32), [3, 3]],
        'desc_bprop': [3, 3],
        'skip': ['backward']}),
    ('BinaryCrossEntropy', {
        'block': P.BinaryCrossEntropy(),
        'desc_inputs': [Tensor([[0.3, 0.8], [0.4, 0.3]], mstype.float16),
                        Tensor([[0.4, 1.2], [-0.4, -0.9]], mstype.float16),
                        Tensor([[-1.4, -0.7], [0.9, 0.7]], mstype.float16)],
        'desc_bprop': []}),
    ('BinaryCrossEntropyGrad', {
        'block': G.BinaryCrossEntropyGrad(),
        'desc_inputs': [Tensor([[0.3, 0.8], [0.4, 0.3]], mstype.float16),
                        Tensor([[0.4, 1.2], [-0.4, -0.9]], mstype.float16), Tensor(0.85, mstype.float16),
                        Tensor([[-1.4, -0.7], [0.9, 0.7]], mstype.float16)],
        'desc_bprop': [],
        'skip': ['backward']}),
    ('SparseApplyAdagrad', {
        'block': P.SparseApplyAdagrad(0.5),
        'desc_inputs': [Tensor([[0.7, 0.2], [0.1, 0.07]], mstype.float32),
                        Tensor([[0.2, 0.2], [0.1, 0.4]], mstype.float32),
                        Tensor([[0.5, 0.4], [0.6, 0.1]], mstype.float32), Tensor([1, 1], mstype.int32)],
        'desc_bprop': [Tensor([[0.7, 0.2], [0.1, 0.07]], mstype.float32)],
        'skip': ['backward']}),
]

test_case_array_ops = [
    ('SpaceToDepth', {
        'block': P.SpaceToDepth(2),
        'desc_inputs': [[1, 3, 2, 2]],
        'desc_bprop': [[1, 12, 1, 1]]}),
    ('DepthToSpace', {
        'block': P.DepthToSpace(2),
        'desc_inputs': [[1, 12, 1, 1]],
        'desc_bprop': [[1, 3, 2, 2]]}),
    ('Split', {
        'block': P.Split(1, 2),
        'desc_inputs': [Tensor(np.array([[1, 1, 1, 1], [2, 2, 2, 2]]))],
        'skip': ['backward']}),
    ('Argmax', {
        'block': P.Argmax(),
        'desc_inputs': [[128, 32, 32, 64]],
        'desc_bprop': [0],
        'skip': ['backward']}),
    ('Argmin', {
        'block': P.Argmin(),
        'desc_inputs': [[128, 32, 32, 64]],
        'desc_bprop': [1],
        'skip': ['backward']}),
    ('ArgMaxWithValue', {
        'block': P.ArgMaxWithValue(),
        'desc_inputs': [[128, 32, 32, 64]],
        'desc_bprop': [[1], [1]],
        'skip': ['backward']}),
    ('ArgMinWithValue', {
        'block': P.ArgMinWithValue(),
        'desc_inputs': [[128, 32, 32, 64]],
        'desc_bprop': [[1], [1]],
        'skip': ['backward']}),
    ('Transpose_dim3', {
        'block': P.Transpose(),
        'desc_const': [(0, 2, 1)],
        'desc_inputs': [[1, 2, 3]],
        'desc_bprop': [[1, 3, 2]]}),
    ('Transpose_dim4', {
        'block': P.Transpose(),
        'desc_const': [(0, 1, 2, 3)],
        'desc_inputs': [[1, 2, 3, 4]],
        'desc_bprop': [[1, 2, 4, 3]]}),
    ('AddN', {
        'block': NetForTupleInput(P.AddN()),
        'desc_inputs': [[2, 3, 3, 5], [2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]],
        'skip': ['backward']}),
    ('Shape', {
        'block': P.Shape(),
        'desc_inputs': [[3, 3, 2, 2]],
        'skip': ['backward']}),
    ('Reshape', {
        'block': P.Reshape(),
        'desc_const': [(64,)],
        'desc_inputs': [[64, 1]],
        'desc_bprop': [[64]]}),
    ('Cast', {
        'block': P.Cast(),
        'desc_const': [mstype.int32],
        'desc_inputs': [[2, 3, 4, 5]],
        'desc_bprop': [Tensor(np.ones((2, 3, 4, 5)).astype(np.int32))]}),
    ('ExpandDims', {
        'block': P.ExpandDims(),
        'desc_const': [0],
        'desc_inputs': [[2, 2]],
        'desc_bprop': [[1, 2, 2]]}),
    ('ExpandDims_1', {
        'block': P.ExpandDims(),
        'desc_const': [-1],
        'desc_inputs': [[2, 2]],
        'desc_bprop': [[2, 2, 1]]}),
    ('Squeeze', {
        'block': P.Squeeze(2),
        'desc_inputs': [[3, 2, 1]],
        'desc_bprop': [[3, 2]]}),
    ('Squeeze_0', {
        'block': P.Squeeze(),
        'desc_inputs': [[3, 1, 2, 1]],
        'desc_bprop': [[3, 2]]}),
    ('Squeeze_1', {
        'block': P.Squeeze(),
        'desc_inputs': [[1, 1, 1, 1]],
        'desc_bprop': [1.0],
        'skip': ['backward']}),
    ('Squeeze_2', {
        'block': P.Squeeze((2, 3)),
        'desc_inputs': [[3, 2, 1, 1]],
        'desc_bprop': [[3, 2]]}),
    ('Size', {
        'block': P.Size(),
        'desc_inputs': [[2, 3, 5]],
        'skip': ['backward']}),
    ('Tile_0', {
        'block': P.Tile(),
        'desc_const': [(1, 2)],
        'desc_inputs': [[64, 1]],
        'desc_bprop': [[64, 2]]}),
    ('Tile_1', {
        'block': P.Tile(),
        'desc_const': [(1, 1)],
        'desc_inputs': [[64, 1]],
        'desc_bprop': [[64, 1]]}),
    ('Tile_2', {
        'block': P.Tile(),
        'desc_const': [(2, 1, 1, 2)],
        'desc_inputs': [[2, 2, 2]],
        'desc_bprop': [[2, 2, 2, 4]]}),
    ('ConcatV2_0', {
        'block': P.Concat(),
        'desc_inputs': [
            (Tensor(np.array([[0, 1], [2, 1]]).astype(np.int32)),
             Tensor(np.array([[0, 1], [2, 1]]).astype(np.int32)))],
        'desc_bprop': [([4, 2], {'dtype': np.int32})]}),
    ('ConcatV2_1', {
        'block': P.Concat(axis=2),
        'desc_inputs': [(Tensor(np.array([[[0, 1, 2]], [[2, 1, 2]]]).astype(np.int32)),
                         Tensor(np.array([[[0, 1]], [[2, 1]]]).astype(np.int32)))],
        'desc_bprop': [([2, 1, 5], {'dtype': np.int32})]}),
    ('ConcatV2_2', {
        'block': NetForConcat(),
        'desc_inputs': [[2, 2]],
        'desc_bprop': [[4, 2]]}),
    ('ConcatV2_3', {
        'block': NetForConcat1(),
        'desc_inputs': [[2, 2], [2, 2]],
        'desc_bprop': [[4, 2]]}),
    ('ConcatV2_4', {
        'block': P.Concat(axis=0),
        'desc_inputs': [
            (Tensor(np.ones((3, 2, 3), np.float32)),
             Tensor(np.ones((5, 2, 3), np.float32)),
             Tensor(np.ones((6, 2, 3), np.float32)))],
        'desc_bprop': [[14, 2, 3]]}),
    ('ConcatV2_5', {
        'block': P.Concat(axis=-1),
        'desc_inputs': [(Tensor(np.array([1], np.float32)),
                         Tensor(np.array([1], np.float32)),
                         Tensor(np.array([1], np.float32)))],
        'desc_bprop': [[3,]]}),
    ('Pack_0', {
        'block': NetForPackInput(P.Pack()),
        'desc_inputs': [[2, 2], [2, 2], [2, 2]],
        'desc_bprop': [[3, 2, 2]],
    }),
    ('Pack_1', {
        'block': NetForPackInput(P.Pack(axis=-2)),
        'desc_inputs': [[3, 2, 3], [3, 2, 3], [3, 2, 3]],
        'desc_bprop': [[3, 2, 3, 3]],
    }),
    ('Pack_2', {
        'block': NetForPackInput(P.Pack()),
        'desc_inputs': [[128, 128], [128, 128]],
        'desc_bprop': [[2, 128, 128]],
    }),
    ('Unpack_0', {
        'block': NetForUnpackInput(P.Unpack(axis=0)),
        'desc_inputs': [[2, 4]],
        'desc_bprop': [[4], [4]],
    }),
    ('Unpack_1', {
        'block': NetForUnpackInput(P.Unpack(axis=-1)),
        'desc_inputs': [Tensor(np.array([[1, 1, 1]], np.float32))],
        'desc_bprop': [[1], [1], [1]],
    }),
    ('Diag_1', {
        'block': P.Diag(),
        'desc_inputs': [[4]],
        'desc_bprop': [[4, 4]],
    }),
    ('Diag_2', {
        'block': P.Diag(),
        'desc_inputs': [[4, 4]],
        'desc_bprop': [[4, 4, 4, 4]],
    }),
    ('DiagPart_1', {
        'block': P.DiagPart(),
        'desc_inputs': [[4, 4]],
        'desc_bprop': [[4]],
    }),
    ('DiagPart_2', {
        'block': P.DiagPart(),
        'desc_inputs': [[4, 4, 4, 4]],
        'desc_bprop': [[4, 4]],
    }),
    ('SpaceToBatch_1', {
        'block': P.SpaceToBatch(2, [[0, 0], [0, 0]]),
        'desc_inputs': [[1, 3, 2, 2]],
        'desc_bprop': [[4, 3, 1, 1]],
    }),
    ('SpaceToBatch_2', {
        'block': P.SpaceToBatch(2, [[1, 1], [0, 4]]),
        'desc_inputs': [[1, 3, 2, 2]],
        'desc_bprop': [[4, 3, 2, 3]],
    }),
    ('BatchToSpace_1', {
        'block': P.BatchToSpace(2, [[0, 0], [0, 0]]),
        'desc_inputs': [[4, 3, 1, 1]],
        'desc_bprop': [[1, 3, 2, 2]],
    }),
    ('BatchToSpace_2', {
        'block': P.BatchToSpace(2, [[0, 0], [0, 1]]),
        'desc_inputs': [[4, 3, 1, 1]],
        'desc_bprop': [[1, 3, 2, 1]],
    }),
    ('UnsortedSegmentMin_1', {
        'block': P.UnsortedSegmentMin(),
        'desc_const': [2],
        'desc_inputs': [Tensor(np.array([[1, 2, 3], [4, 5, 6], [4, 2, 1]]).astype(np.float32)),
                        Tensor(np.array([0, 1, 1]).astype(np.int32))],
        'desc_bprop': [Tensor(np.array([[1, 2, 3], [4, 2, 1]]).astype(np.float32))]}),
    ('BroadcastTo', {
        'block': P.BroadcastTo((2,3)),
        'desc_inputs': [Tensor(np.array([1, 2, 3]).astype(np.float32))],
        'desc_bprop': [Tensor(np.array([[1, 2, 3], [1, 2, 3]]).astype(np.float32))]}),
]

test_case_other_ops = [
    ('ScalarLog', {
        'block': F.scalar_log,
        'desc_const': [0.0],
        'desc_inputs': [],
        'desc_bprop': [1],
        'skip': ['backward']}),
    ('BoundingBoxEncode', {
        'block': P.BoundingBoxEncode(means=(0.0, 0.0, 0.0, 0.0), stds=(1.0, 1.0, 1.0, 1.0)),
        'desc_inputs': [[256, 4], [256, 4]],
        'desc_bprop': [[256, 4]],
        'skip': ['backward']}),
    ('BoundingBoxDecode', {
        'block': P.BoundingBoxDecode(means=(0.0, 0.0, 0.0, 0.0), stds=(1.0, 1.0, 1.0, 1.0), max_shape=(768, 1280)),
        'desc_inputs': [[256, 4], [256, 4]],
        'desc_bprop': [[256, 4]],
        'skip': ['backward']}),
    ('GatherNd', {
        'block': P.GatherNd(),
        'desc_inputs': (Tensor(np.ones((1, 3, 6, 6), np.float32)),
                        Tensor(np.ones((2, 4), np.int32))),
        'desc_bprop': [[2]]}),
    ('ScatterNd', {
        'block': P.ScatterNd(),
        'desc_const': [(3, 3)],
        'desc_inputs': (Tensor(np.ones((2, 2), np.int32)),
                        Tensor(np.ones((2,), np.int32))),
        'desc_bprop': [([3, 3], {'dtype': np.int32})]}),
    ('ScatterMax', {
        'block': ScatterMax(),
        'desc_inputs': (Tensor(np.array([[0, 0], [1, 1]], np.int32)),
                        Tensor(np.ones([2, 2, 3], np.float32) * 99)),
        'skip': ['backward']}),
    ('ScatterAdd', {
        'block': ScatterAdd((6,)),
        'desc_inputs': (Tensor(np.array([2, 0, 5], np.int32)),
                        Tensor(np.array([2.0, 3.0, 4.0], np.float32))),
        'skip': ['backward']}),
    ('ScatterAdd2d', {
        'block': ScatterAdd((3, 4)),
        'desc_inputs': (Tensor(np.array([[0, 1], [1, 2]], np.int32)),
                        Tensor(np.array([[[1, 1, 1, 1], [2, 2, 2, 2]],
                                         [[3, 3, 3, 3], [4, 4, 4, 4]]], np.float32))),
        'skip': ['backward']}),
    ('SmoothL1Loss', {
        'block': P.SmoothL1Loss(),
        'desc_inputs': [[256, 4], [256, 4]],
        'desc_bprop': [[256, 4]]}),
    ('IOU', {
        'block': P.IOU(),
        'desc_inputs': [Tensor(np.ones((256, 4), np.float16)), Tensor(np.ones((128, 4), np.float16))],
        'desc_bprop': [[128, 256]]}),
    ('Summary', {
        'block': SummaryNet(),
        'desc_inputs': [Tensor(np.array([1.1]).astype(np.float32)),
                        Tensor(np.array([1.2]).astype(np.float32))],
        'skip': ['backward']}),
    ('ConfusionMulGrad_1', {
        'block': P.ConfusionMulGrad(axis=[0], keep_dims=False),
        'desc_inputs': [[3, 2], [3, 2], [3, 2]],
        'desc_bprop': [[3, 2], [2]],
        'skip': ['backward']}),
    ('ConfusionMulGrad_2', {
        'block': P.ConfusionMulGrad(axis=[0], keep_dims=True),
        'desc_inputs': [[3, 2], [3, 2], [3, 2]],
        'desc_bprop': [[3, 2], [1, 2]],
        'skip': ['backward']}),
    ('ConfusionMulGrad_3', {
        'block': P.ConfusionMulGrad(axis=(), keep_dims=True),
        'desc_inputs': [[2, 3, 4], [2, 3, 4], [2, 3, 4]],
        'desc_bprop': [[2, 3, 4], [1, 1, 1]],
        'skip': ['backward']}),
    ('HistogramSummary', {
        'block': HistogramSummaryNet(),
        'desc_inputs': [Tensor(np.array([1.1]).astype(np.float32)),
                        Tensor(np.array([1.2]).astype(np.float32))],
        'skip': ['backward']}),

]

test_case_lists = [test_case_nn_ops, test_case_math_ops, test_case_array_ops, test_case_other_ops]
test_case = functools.reduce(lambda x, y: x + y, test_case_lists)
# use -k to select certain testcast
# pytest tests/python/ops/test_ops.py::test_backward -k LayerNorm


test_exec_case = test_case

test_backward_exec_case = filter(lambda x: 'skip' not in x[1] or 'backward' not in x[1]['skip'], test_case)


@non_graph_engine
@mindspore_test(pipeline_for_compile_forward_ge_graph_for_case_by_case_config)
def test_exec():
    context.set_context(mode=context.GRAPH_MODE)
    return test_exec_case


@mindspore_test(pipeline_for_compile_grad_ge_graph_for_case_by_case_config)
def test_backward_exec():
    context.set_context(mode=context.GRAPH_MODE)
    return test_backward_exec_case


raise_set = [
    ('Cast_Error', {
        'block': (P.Cast(), {'exception': TypeError}),
        'desc_const': [mstype.int32],
        'desc_inputs': ['wrong input'],
        'desc_bprop': [Tensor(np.ones((2, 3, 3, 5)).astype(np.int32))]}),
    ('Maximum_Error', {
        'block': (P.Maximum(), {'exception': TypeError}),
        'desc_const': [(1, 2, 3)],
        'desc_inputs': [[2, 3, 3, 5]],
        'desc_bprop': [[2, 3, 3, 5]]}),
    ('Shape_error', {
        'block': (P.Shape(), {'exception': TypeError}),
        'desc_inputs': [(64, 1)],
        'desc_bprop': [[64]]}),
    ('Flatten_Error', {
        'block': (NetForFlatten0D(), {'exception': ValueError}),
        'desc_inputs': [Tensor(np.array(0).astype(np.int32))],
        'desc_bprop': [Tensor(np.array(0).astype(np.int32))]}),
    ('ScatterNdUpdate', {
        'block': (P.ScatterNdUpdate(), {'exception': TypeError}),
        'desc_inputs': (Tensor(np.ones((2, 3), np.float32)),
                        Tensor(np.ones((2, 2), np.float32)),
                        Tensor(np.ones((2,), np.float32))),
        'desc_bprop': [[2, 3]]}),
    ('Pack', {
        'block': (NetForPackInput(P.Pack()), {'exception': ValueError}),
        'desc_inputs': [[2, 2]],
        'desc_bprop': [[1, 2, 2]]}),
    ('PReLU', {
        'block': (P.PReLU(), {'exception': ValueError}),
        'desc_inputs': [[2], [1]],
        'desc_bprop': [[1]]}),

]


@mindspore_test(pipeline_for_compile_forward_ge_graph_for_case_by_case_config_exception)
def test_check_exception():
    return raise_set
