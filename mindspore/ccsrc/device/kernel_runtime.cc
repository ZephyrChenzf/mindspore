/**
 * Copyright 2019 Huawei Technologies Co., Ltd
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "device/kernel_runtime.h"
#include <vector>
#include <utility>
#include <numeric>
#include <functional>
#include "common/utils.h"
#include "common/trans.h"
#include "utils/utils.h"
#include "utils/context/ms_context.h"
#include "operator/ops.h"
#include "pipeline/parse/python_adapter.h"
#include "session/kernel_graph.h"
#include "session/anf_runtime_algorithm.h"
#include "kernel/common_utils.h"
#include "kernel/oplib/oplib.h"
#include "ir/value.h"
using mindspore::kernel::Address;
using mindspore::kernel::AddressPtr;

namespace mindspore {
namespace device {
KernelRuntime::~KernelRuntime() {
#ifdef ENABLE_DUMP_E2E
  dump_conf_ptr_ = nullptr;
#endif
}

bool KernelRuntime::Run(session::KernelGraph *graph) {
  bool ret = false;
  auto context_ptr = MsContext::GetInstance();
  MS_EXCEPTION_IF_NULL(context_ptr);
#if defined(_WIN32) || defined(_WIN64)
  auto start_time = std::chrono::steady_clock::now();
#else
  struct timeval start_time, end_time;
  (void)gettimeofday(&start_time, nullptr);
#endif
  bool is_task_sink = context_ptr->enable_task_sink();
  if (is_task_sink) {
    ret = RunTask(graph);
  } else {
    ret = LaunchKernel(graph);
  }
#if defined(_WIN32) || defined(_WIN64)
  auto end_time = std::chrono::steady_clock::now();
  std::chrono::duration<double, std::ratio<1, 1000000>> cost = end_time - start_time;
  MS_LOG(INFO) << "Call MS Run Success in " << cost.count() << " us";
#else
  (void)gettimeofday(&end_time, nullptr);
  const uint64_t kUSecondInSecond = 1000000;
  uint64_t cost = kUSecondInSecond * static_cast<uint64_t>(end_time.tv_sec - start_time.tv_sec);
  cost += static_cast<uint64_t>(end_time.tv_usec - start_time.tv_usec);
  MS_LOG(INFO) << "Call MS Run Success in " << cost << " us";
#endif
  return ret;
}

// for D to impl
bool KernelRuntime::DumpData(mindspore::session::KernelGraph *graph) {
  if (graph != nullptr) {
    return true;
  }
  return false;
}

// for D to impl
bool KernelRuntime::GenTask(const session::KernelGraph *graph) {
  if (graph != nullptr) {
    return true;
  }
  return false;
}

bool KernelRuntime::LoadTask(const session::KernelGraph *graph) {
  if (graph != nullptr) {
    return true;
  }
  return false;
}

// for D to impl
bool KernelRuntime::RunTask(const session::KernelGraph *graph) {
  if (graph != nullptr) {
    return true;
  }
  return false;
}

bool KernelRuntime::NodeOutputDeviceAddressExist(const AnfNodePtr &kernel, size_t index) {
  if (AnfAlgo::OutputAddrExist(kernel, index)) {
    return true;
  }
  return false;
}

size_t KernelRuntime::CountNodeDeviceMemorySize(const mindspore::AnfNodePtr &node, size_t output_index) {
  MS_EXCEPTION_IF_NULL(node);
  if (output_index >= AnfAlgo::GetOutputTensorNum(node)) {
    MS_EXCEPTION(ArgumentError) << "output index [" << output_index << "] large than the output size ["
                                << AnfAlgo::GetOutputTensorNum(node) << "] of node!";
  }
  TypeId output_type_id = AnfAlgo::GetOutputDeviceDataType(node, output_index);
  if (output_type_id == kTypeUnknown) {
    output_type_id = AnfAlgo::GetOutputInferDataType(node, output_index);
  }
  size_t type_size = GetTypeByte(TypeIdToType(output_type_id));
  std::vector<size_t> shape = AnfAlgo::GetOutputDeviceShape(node, output_index);
  auto format = AnfAlgo::GetOutputFormat(node, output_index);
  if (shape.empty() && format != kOpFormat_DEFAULT) {
    shape = trans::PaddingShapeTo4d(shape, AnfAlgo::GetOutputReshapeType(node, output_index));
    shape = trans::TransShapeToDevice(shape, format);
  }
  // scalar's output shape is a empty vector
  size_t tensor_size = std::accumulate(shape.begin(), shape.end(), type_size, std::multiplies<size_t>());
  return tensor_size;
}

void KernelRuntime::AssignMemory(session::KernelGraph *graph) {
  auto context_ptr = MsContext::GetInstance();
  MS_EXCEPTION_IF_NULL(context_ptr);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  mem_manager_->ResetDynamicMemory();
  AssignStaticMemory(graph);
  AssignDynamicMemory(graph);
  UpdateRefNodeOutputMem(graph);
}

void KernelRuntime::RunOpAssignMemory(const std::vector<tensor::TensorPtr> &input_tensors,
                                      session::KernelGraph *graph) {
  MS_EXCEPTION_IF_NULL(graph);
  RunOpAssignInputMemory(input_tensors, graph);
  AssignStaticMemoryValueNode(graph);
  for (const auto &cnode : graph->execution_order()) {
    RunOpAssignOutputMemory(cnode);
    RunOpAssignWorkSpaceMemory(cnode);
  }
  UpdateRefNodeOutputMem(graph);
}

void KernelRuntime::AssignStaticMemory(session::KernelGraph *graph) {
  AssignStaticMemoryInput(graph);
  AssignStaticMemoryValueNode(graph);
  AssignStaticMemoryOutput(graph);
}

void KernelRuntime::RunOpAssignInputMemory(const std::vector<tensor::TensorPtr> &input_tensors,
                                           const session::KernelGraph *graph) {
  MS_EXCEPTION_IF_NULL(graph);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  if (input_tensors.size() != graph->inputs().size()) {
    MS_LOG(EXCEPTION) << "Input tensors size " << input_tensors.size()
                      << " should be equal to graph input parameter size " << graph->inputs().size();
  }

  for (size_t input_index = 0; input_index < graph->inputs().size(); ++input_index) {
    auto item = graph->inputs()[input_index];
    MS_EXCEPTION_IF_NULL(item);
    if (!item->isa<Parameter>()) {
      continue;
    }
    auto output_size = AnfAlgo::GetOutputTensorNum(item);
    for (size_t index = 0; index < output_size; index++) {
      MS_EXCEPTION_IF_NULL(input_tensors[input_index]);
      if (input_tensors[input_index]->device_address().get() != nullptr) {
        AnfAlgo::SetOutputAddr(input_tensors[input_index]->device_address(), index, item.get());
        continue;
      }
      TypeId output_type_id = AnfAlgo::GetOutputDeviceDataType(item, index);
      if (output_type_id == kTypeUnknown) {
        output_type_id = AnfAlgo::GetOutputInferDataType(item, index);
      }
      auto tensor_size = CountNodeDeviceMemorySize(item, index);
      auto device_address =
        CreateDeviceAddress(nullptr, tensor_size, AnfAlgo::GetOutputFormat(item, index), output_type_id);
      MS_EXCEPTION_IF_NULL(device_address);
      auto ret = mem_manager_->MallocMemFromMemPool(device_address, tensor_size);
      if (!ret) {
        MS_LOG(EXCEPTION) << "Malloc device memory failed.";
      }
      AnfAlgo::SetOutputAddr(device_address, index, item.get());
    }
  }
}

void KernelRuntime::RunOpAssignOutputMemory(const AnfNodePtr &kernel) {
  MS_EXCEPTION_IF_NULL(kernel);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  auto kernel_mod = AnfAlgo::GetKernelMod(kernel);
  MS_EXCEPTION_IF_NULL(kernel_mod);
  auto output_sizes = kernel_mod->GetOutputSizeList();
  if (output_sizes.empty()) {
    return;
  }

  for (size_t i = 0; i < output_sizes.size(); ++i) {
    if (AnfAlgo::OutputAddrExist(kernel, i)) {
      continue;
    }
    if (AnfAlgo::GetCNodeName(kernel) == kApplyMomentumOpName) {
      auto device_address = AnfAlgo::GetPrevNodeMutableOutputAddr(kernel, i);
      AnfAlgo::SetOutputAddr(device_address, i, kernel.get());
      continue;
    }
    std::string output_format = AnfAlgo::GetOutputFormat(kernel, i);
    auto output_type = AnfAlgo::GetOutputDeviceDataType(kernel, i);
    auto device_address = CreateDeviceAddress(nullptr, output_sizes[i], output_format, output_type);
    MS_EXCEPTION_IF_NULL(device_address);
    auto ret = mem_manager_->MallocMemFromMemPool(device_address, output_sizes[i]);
    if (!ret) {
      MS_LOG(EXCEPTION) << "Malloc device memory failed.";
    }
    AnfAlgo::SetOutputAddr(device_address, i, kernel.get());
  }
}

void KernelRuntime::RunOpAssignWorkSpaceMemory(const AnfNodePtr &kernel) {
  MS_EXCEPTION_IF_NULL(kernel);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  if (kernel->isa<CNode>()) {
    auto kernel_mod = AnfAlgo::GetKernelMod(kernel);
    MS_EXCEPTION_IF_NULL(kernel_mod);
    auto workspace_lists = kernel_mod->GetWorkspaceSizeList();
    for (size_t i = 0; i < workspace_lists.size(); ++i) {
      auto device_address = CreateDeviceAddress(nullptr, workspace_lists[i], "", kTypeUnknown);
      MS_EXCEPTION_IF_NULL(device_address);
      auto ret = mem_manager_->MallocMemFromMemPool(device_address, workspace_lists[i]);
      if (!ret) {
        MS_LOG(EXCEPTION) << "Malloc device memory failed.";
      }
      AnfAlgo::SetWorkspaceAddr(device_address, i, kernel.get());
    }
  }
}

void KernelRuntime::AssignStaticMemoryInput(const session::KernelGraph *graph) {
  MS_EXCEPTION_IF_NULL(graph);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  auto graph_inputs = graph->inputs();
  auto graph_valid_input = graph->valid_inputs();
  for (size_t i = 0; i < graph_inputs.size(); i++) {
    auto item = graph_inputs[i];
    MS_EXCEPTION_IF_NULL(item);
    if (!item->isa<Parameter>()) {
      continue;
    }
    if (i < graph_valid_input.size() && !graph_valid_input[i]) {
      continue;
    }
    if (NodeOutputDeviceAddressExist(item, 0)) {
      continue;
    }
    auto output_size = AnfAlgo::GetOutputTensorNum(item);
    for (size_t index = 0; index < output_size; index++) {
      TypeId output_type_id = AnfAlgo::GetOutputDeviceDataType(item, index);
      // if graph output is a weight and doesn't link to any cnode, it's data type will be unknown
      if (output_type_id == kTypeUnknown) {
        MS_LOG(WARNING) << "It is not suggested to use a lonely weight parameter as the output of graph";
        output_type_id = AnfAlgo::GetOutputInferDataType(item, index);
      }
      auto tensor_size = CountNodeDeviceMemorySize(item, index);
      auto ptr = mem_manager_->MallocMem(kStaticMem, tensor_size);
      auto address = CreateDeviceAddress(ptr, tensor_size, AnfAlgo::GetOutputFormat(item, index), output_type_id);
      AnfAlgo::SetOutputAddr(address, index, item.get());
    }
  }
}

void KernelRuntime::AssignStaticMemoryOutput(const session::KernelGraph *graph) {
  MS_EXCEPTION_IF_NULL(graph);
  auto nodes = AnfAlgo::GetAllOutput(graph->output(), {prim::kPrimTupleGetItem});
  std::vector<session::KernelWithIndex> non_communication_op;
  // Assign Communicate Op Memory firstly.
  for (const auto &node : nodes) {
    auto item_with_index = AnfAlgo::VisitKernelWithReturnType(node, 0, true);
    MS_EXCEPTION_IF_NULL(item_with_index.first);
    if (!item_with_index.first->isa<CNode>() || !AnfAlgo::IsRealKernel(item_with_index.first)) {
      continue;
    }
    if (AnfAlgo::IsCommunicationOp(item_with_index.first)) {
      AssignCommunicationNodeMem(kStaticMem, item_with_index.first);
    } else {
      non_communication_op.emplace_back(item_with_index);
    }
  }

  for (const auto &item_with_index : non_communication_op) {
    AssignNodeOutputMem(kStaticMem, item_with_index.first, SizeToInt(item_with_index.second));
  }
}

void KernelRuntime::UpdateRefNodeOutputMem(const session::KernelGraph *graph) {
  MS_EXCEPTION_IF_NULL(graph);
  auto &kernels = graph->execution_order();
  for (auto &kernel : kernels) {
    MS_EXCEPTION_IF_NULL(kernel);
    auto kernel_mod = AnfAlgo::GetKernelMod(kernel);
    MS_EXCEPTION_IF_NULL(kernel_mod);

    auto output_sizes = kernel_mod->GetOutputSizeList();
    if (output_sizes.empty()) {
      MS_LOG(INFO) << "This kernel has no output size.";
      continue;
    }
    for (size_t i = 0; i < output_sizes.size(); ++i) {
      session::AnfWithOutIndex out_pair(kernel, i);
      if (graph->IsInRefOutputMap(out_pair)) {
        auto origin_pair = graph->GetRefCorrespondOutput(out_pair);
        MS_EXCEPTION_IF_NULL(origin_pair.first);
        auto origin_node_output_addr = AnfAlgo::GetMutableOutputAddr(origin_pair.first, origin_pair.second);
        MS_EXCEPTION_IF_NULL(origin_node_output_addr);
        auto cur_node_output_addr = AnfAlgo::GetMutableOutputAddr(kernel, i);
        if (origin_node_output_addr.get() != cur_node_output_addr.get()) {
          MS_LOG(INFO) << "REF address is not same, ref node output need address update";
          MS_LOG(INFO) << "REF origin op is " << origin_pair.first->DebugString() << ", output index is "
                       << origin_pair.second << ", cur op is " << kernel->DebugString() << ", out index is " << i;
          AnfAlgo::SetOutputAddr(origin_node_output_addr, i, kernel.get());
        }
      }
    }
  }
}

void KernelRuntime::AssignCommunicationNodeMem(int flag, const AnfNodePtr &node) {
  AssignCommunicationNodeInputMem(node);
  AssignCommunicationNodeOutputMem(flag, node);
}

void KernelRuntime::AssignCommunicationNodeOutputMem(int flag, const AnfNodePtr &node) {
  MS_EXCEPTION_IF_NULL(node);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  auto kernel_mod = AnfAlgo::GetKernelMod(node);
  MS_EXCEPTION_IF_NULL(kernel_mod);
  auto output_sizes = kernel_mod->GetOutputSizeList();
  if (output_sizes.empty()) {
    MS_LOG(INFO) << "This kernel[" << node->DebugString() << "] has no output size.";
    return;
  }
  auto context_ptr = MsContext::GetInstance();
  MS_EXCEPTION_IF_NULL(context_ptr);
  size_t total_size = 0;
  size_t output_index = 0;
  std::vector<size_t> align_size_list;
  for (uint64_t mem_size : output_sizes) {
    if (AnfAlgo::OutputAddrExist(node, output_index++)) {
      MS_LOG(INFO) << "communication op addr exist";
      continue;
    }
    if (context_ptr->enable_hccl()) {
      mem_size = mem_manager_->GetCommonAlignSize(mem_size);
    }
    total_size += mem_size;
    align_size_list.emplace_back(mem_size);
  }
  uint8_t *output_ptr = mem_manager_->MallocOutputMem(node, 0, flag, total_size);
  for (size_t j = 0; j < align_size_list.size(); ++j) {
    std::string output_format = AnfAlgo::GetOutputFormat(node, j);
    auto output_type = AnfAlgo::GetOutputDeviceDataType(node, j);
    auto address = CreateDeviceAddress(output_ptr, output_sizes[j], output_format, output_type);
    AnfAlgo::SetOutputAddr(address, j, node.get());
    output_ptr += align_size_list[j];
  }
}

DeviceAddressPtr KernelRuntime::PreAssignCNodeMemory(const AnfNodePtr &anf_node, size_t index) {
  MS_EXCEPTION_IF_NULL(anf_node);
  auto kernel_mod = AnfAlgo::GetKernelMod(anf_node);
  auto output_sizes = kernel_mod->GetOutputSizeList();
  if (output_sizes.size() <= index) {
    MS_LOG(EXCEPTION) << "Previous node output size < node index";
  }
  std::string output_format = AnfAlgo::GetOutputFormat(anf_node, index);
  auto output_type = AnfAlgo::GetOutputDeviceDataType(anf_node, index);
  auto address = CreateDeviceAddress(nullptr, output_sizes[index], output_format, output_type);
  AnfAlgo::SetOutputAddr(address, index, anf_node.get());
  return address;
}

void KernelRuntime::AssignCommunicationNodeInputMem(const AnfNodePtr &node) {
  auto context_ptr = MsContext::GetInstance();
  MS_EXCEPTION_IF_NULL(context_ptr);
  MS_EXCEPTION_IF_NULL(node);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  size_t total_size = 0;
  std::vector<std::pair<mindspore::device::DeviceAddress *, size_t>> addr_size;
  for (size_t i = 0; i < AnfAlgo::GetInputTensorNum(node); ++i) {
    auto input_node_with_index = AnfAlgo::GetPrevNodeOutput(node, i);
    auto input_node = input_node_with_index.first;
    DeviceAddressPtr address = nullptr;
    if (input_node->isa<CNode>()) {
      address = PreAssignCNodeMemory(input_node, input_node_with_index.second);
    } else {
      MS_LOG(EXCEPTION) << "Communication node inputs only support CNode";
    }
    MS_EXCEPTION_IF_NULL(address);
    auto mem_size = mem_manager_->GetCommonAlignSize(address->size());
    total_size += mem_size;
    addr_size.emplace_back(address.get(), mem_size);
  }
  uint8_t *input_ptr = mem_manager_->MallocOutputMem(node, 0, kDynamicMem, total_size);
  for (const auto &iter : addr_size) {
    MS_EXCEPTION_IF_NULL(iter.first);
    iter.first->set_ptr(input_ptr);
    input_ptr += iter.second;
  }
}

void KernelRuntime::AssignNodeOutputMem(int flag, const AnfNodePtr &node, int index) {
  MS_EXCEPTION_IF_NULL(node);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  if (AnfAlgo::IsGetNext(NOT_NULL(node)) && flag == kReuseDynamicMem) {
    MS_LOG(INFO) << "GetNext disable mem_reuse";
    flag = kDynamicMem;
  }
  auto kernel_mod = AnfAlgo::GetKernelMod(node);
  MS_EXCEPTION_IF_NULL(kernel_mod);
  auto output_sizes = kernel_mod->GetOutputSizeList();
  if (output_sizes.empty()) {
    MS_LOG(INFO) << "This kernel[" << node->DebugString() << "] has no output size.";
    return;
  }
  for (size_t i = 0; i < output_sizes.size(); ++i) {
    if ((kGetAllOuts != index) && (SizeToInt(i) != index)) {
      continue;
    }
    if (NodeOutputDeviceAddressExist(node, i)) {
      MS_LOG(INFO) << "Already malloc index:" << i;
      continue;
    }
    auto ptr = mem_manager_->MallocOutputMem(node, i, flag, output_sizes[i]);
    if (ptr == nullptr) {
      // reused ptr, no need alloc, continue;
      continue;
    }
    std::string output_format = AnfAlgo::GetOutputFormat(node, i);
    auto output_type = AnfAlgo::GetOutputDeviceDataType(node, i);
    AnfAlgo::SetOutputAddr(CreateDeviceAddress(ptr, output_sizes[i], output_format, output_type), i, node.get());
  }
}

void KernelRuntime::AssignValueNodeTensor(const ValueNodePtr &value_node, const ValuePtr &node_value,
                                          size_t output_idx) {
  MS_EXCEPTION_IF_NULL(value_node);
  MS_EXCEPTION_IF_NULL(node_value);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  auto ms_context = MsContext::GetInstance();
  MS_EXCEPTION_IF_NULL(ms_context);
  auto tensor = node_value->cast<TensorPtr>();
  if (tensor == nullptr) {
    MS_LOG(WARNING) << "Tensor is null";
    return;
  }
  size_t tensor_size = tensor->data().nbytes();
  auto node_size = CountNodeDeviceMemorySize(value_node, output_idx);
  TypeId output_type_id = AnfAlgo::GetOutputDeviceDataType(value_node, output_idx);
  if (output_type_id == kTypeUnknown) {
    output_type_id = AnfAlgo::GetOutputInferDataType(value_node, output_idx);
  }
  auto output_format = AnfAlgo::GetOutputFormat(value_node, output_idx);
  DeviceAddressPtr address = nullptr;
  if (ms_context->enable_pynative_infer()) {
    address = CreateDeviceAddress(nullptr, node_size, output_format, output_type_id);
    MS_EXCEPTION_IF_NULL(address);
    if (!mem_manager_->MallocMemFromMemPool(address, node_size)) {
      MS_LOG(EXCEPTION) << "Malloc value node device memory failed !";
    }
  } else {
    auto ptr = mem_manager_->MallocMem(kStaticMem, node_size);
    address = CreateDeviceAddress(ptr, node_size, output_format, output_type_id);
    MS_EXCEPTION_IF_NULL(address);
  }
  AnfAlgo::SetOutputAddr(address, output_idx, value_node.get());
  if (!address->SyncHostToDevice(trans::GetRuntimePaddingShape(value_node, 0), tensor_size, tensor->data_type(),
                                 tensor->data_c(false))) {
    MS_EXCEPTION(NotExistsError) << "ValueNode SyncHostToDevice fail!" << value_node->DebugString() << "node format is"
                                 << AnfAlgo::GetOutputFormat(value_node, output_idx) << "node dtype is "
                                 << AnfAlgo::GetOutputInferDataType(value_node, output_idx);
  }
}

void KernelRuntime::AssignStaticMemoryValueNode(session::KernelGraph *graph) {
  MS_EXCEPTION_IF_NULL(graph);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  auto ms_context = MsContext::GetInstance();
  MS_EXCEPTION_IF_NULL(ms_context);
  for (auto &value_node : graph->graph_value_nodes()) {
    MS_EXCEPTION_IF_NULL(value_node);
    if (NodeOutputDeviceAddressExist(value_node, 0)) {
      MS_LOG(INFO) << "value_node[" << value_node->DebugString() << "] address already exist";
      continue;
    }
    auto &node_value = value_node->value();
    MS_EXCEPTION_IF_NULL(node_value);
    if (node_value->isa<Tensor>()) {
      AssignValueNodeTensor(value_node, node_value, 0);
    } else if (node_value->isa<StringImm>()) {
      auto value = GetValue<std::string>(node_value);
      size_t tensor_size = value.size();
      DeviceAddressPtr address = nullptr;
      if (ms_context->enable_pynative_infer()) {
        address = CreateDeviceAddress(nullptr, tensor_size, kOpFormat_DEFAULT, kNumberTypeUInt8);
        MS_EXCEPTION_IF_NULL(address);
        if (!mem_manager_->MallocMemFromMemPool(address, tensor_size)) {
          MS_LOG(EXCEPTION) << "Malloc value node device memory failed !";
        }
      } else {
        auto ptr = mem_manager_->MallocMem(kStaticMem, tensor_size);
        address = CreateDeviceAddress(ptr, tensor_size, kOpFormat_DEFAULT, kNumberTypeUInt8);
        MS_EXCEPTION_IF_NULL(address);
      }
      AnfAlgo::SetOutputAddr(address, 0, value_node.get());
      std::vector<int> shape = {1, SizeToInt(tensor_size)};
      if (!address->SyncHostToDevice(shape, tensor_size, kNumberTypeUInt8, value.data())) {
        MS_LOG(EXCEPTION) << "kValueNode SyncHostToDevice fail!";
      }
    }
  }
}

void KernelRuntime::AssignDynamicMemory(session::KernelGraph *graph) {
  MS_EXCEPTION_IF_NULL(graph);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  auto context_ptr = MsContext::GetInstance();
  MS_EXCEPTION_IF_NULL(context_ptr);
  bool is_enable_mem_reuse = context_ptr->enable_mem_reuse();
  auto mem_flag = kDynamicMem;
  if (is_enable_mem_reuse) {
    mem_manager_->MallocReusedDynamicMem(graph);
    mem_flag = kReuseDynamicMem;
  }
  auto &execution_nodes = graph->execution_order();
  std::vector<CNodePtr> compute_nodes;
  // communication nodes first
  for (auto &node : execution_nodes) {
    if (AnfAlgo::IsCommunicationOp(node)) {
      // skip if the memory is already alocated
      AssignCommunicationNodeMem(mem_flag, node);
    } else {
      compute_nodes.emplace_back(node);
    }
  }

  // then compute nodes
  for (auto &node : compute_nodes) {
    AssignNodeOutputMem(mem_flag, node, kGetAllOuts);
    AssignWorkSpaceMem(mem_flag, node);
  }
}

void KernelRuntime::AssignWorkSpaceMem(int flag, const AnfNodePtr &node) {
  MS_EXCEPTION_IF_NULL(node);
  MS_EXCEPTION_IF_NULL(mem_manager_);
  auto kernel_mod = AnfAlgo::GetKernelMod(node);
  MS_EXCEPTION_IF_NULL(kernel_mod);
  size_t index = 0;
  for (auto &size : kernel_mod->GetWorkspaceSizeList()) {
    auto ptr = mem_manager_->MallocWorkSpaceMem(node, index, flag, size);
    AnfAlgo::SetWorkspaceAddr(CreateDeviceAddress(ptr, size, "", kTypeUnknown), index, node.get());
    index++;
  }
}

void KernelRuntime::GenLaunchArgs(const mindspore::kernel::KernelMod &kernel_mod, const mindspore::AnfNodePtr &kernel,
                                  AddressPtrList *kernel_inputs, AddressPtrList *const kernel_workspaces,
                                  AddressPtrList *kernel_outputs) {
  MS_EXCEPTION_IF_NULL(kernel);
  MS_EXCEPTION_IF_NULL(kernel_inputs);
  MS_EXCEPTION_IF_NULL(kernel_workspaces);
  MS_EXCEPTION_IF_NULL(kernel_outputs);
  auto cnode = kernel->cast<CNodePtr>();
  MS_EXCEPTION_IF_NULL(cnode);
  if (AnfAlgo::GetCNodeName(cnode) == kAtomicAddrCleanOpName) {
    return GenAddrCleanLaunchArgs(cnode, kernel_inputs);
  }
  for (size_t i = 0; i < AnfAlgo::GetInputTensorNum(kernel); ++i) {
    auto real_input = AnfAlgo::GetRealInputIndex(kernel, i);
    auto device_address = AnfAlgo::GetPrevNodeOutputAddr(kernel, real_input);
    kernel::AddressPtr input = std::make_shared<kernel::Address>();
    MS_EXCEPTION_IF_NULL(input);
    input->addr = device_address->ptr_;
    MS_EXCEPTION_IF_NULL(input->addr);
    input->size = device_address->size_;
    kernel_inputs->emplace_back(input);
  }

  for (size_t i = 0; i < kernel_mod.GetOutputSizeList().size(); ++i) {
    auto device_address = AnfAlgo::GetOutputAddr(kernel, i);
    kernel::AddressPtr output = std::make_shared<kernel::Address>();
    MS_EXCEPTION_IF_NULL(output);
    output->addr = device_address->ptr_;
    MS_EXCEPTION_IF_NULL(output->addr);
    output->size = device_address->size_;
    kernel_outputs->emplace_back(output);
  }

  for (size_t i = 0; i < kernel_mod.GetWorkspaceSizeList().size(); ++i) {
    auto device_address = AnfAlgo::GetWorkspaceAddr(kernel, i);
    kernel::AddressPtr workspace = std::make_shared<kernel::Address>();
    MS_EXCEPTION_IF_NULL(workspace);
    workspace->addr = device_address->ptr_;
    MS_EXCEPTION_IF_NULL(workspace->addr);
    workspace->size = device_address->size_;
    kernel_workspaces->emplace_back(workspace);
  }
}

void KernelRuntime::GenAddrCleanLaunchArgs(const CNodePtr &cnode, AddressPtrList *kernel_inputs) {
  if (cnode->inputs().size() != 2) {
    MS_LOG(EXCEPTION) << "Atomic Addr clean Node Input nodes not equal 2.";
  }
  MS_EXCEPTION_IF_NULL(cnode->inputs()[1]);
  auto pre_node = (cnode->inputs()[1])->cast<CNodePtr>();
  // set clean output address
  if (AnfAlgo::HasNodeAttr(kAttrAutomicOutputIndexs, pre_node)) {
    auto clean_output_indexs = AnfAlgo::GetNodeAttr<std::vector<size_t>>(pre_node, kAttrAutomicOutputIndexs);
    for (auto index : clean_output_indexs) {
      auto device_address = AnfAlgo::GetOutputAddr(pre_node, index);
      kernel::AddressPtr input = std::make_shared<kernel::Address>();
      MS_EXCEPTION_IF_NULL(input);
      input->addr = device_address->ptr_;
      MS_EXCEPTION_IF_NULL(input->addr);
      input->size = device_address->size_;
      kernel_inputs->emplace_back(input);
    }
    MS_LOG(INFO) << "AtomicAddClean clean output size:" << clean_output_indexs.size();
  }
  // set clean workspace address
  if (AnfAlgo::HasNodeAttr(kAttrAutomicWorkspaceSize, pre_node)) {
    auto clean_workspaces = AnfAlgo::GetNodeAttr<int>(pre_node, kAttrAutomicWorkspaceSize);
    if (clean_workspaces != 0) {
      auto device_address = AnfAlgo::GetWorkspaceAddr(pre_node, 0);
      kernel::AddressPtr workspace = std::make_shared<kernel::Address>();
      MS_EXCEPTION_IF_NULL(workspace);
      workspace->addr = device_address->ptr_;
      MS_EXCEPTION_IF_NULL(workspace->addr);
      workspace->size = device_address->size_;
      kernel_inputs->emplace_back(workspace);
    }
    MS_LOG(INFO) << "AtomicAddClean clean workspace size" << clean_workspaces;
  }
}

bool KernelRuntime::LaunchKernelMod(const session::KernelGraph &graph) {
  auto &kernels = graph.execution_order();
  for (const auto &kernel : kernels) {
    auto kernel_mod = AnfAlgo::GetKernelMod(kernel);
    MS_EXCEPTION_IF_NULL(kernel_mod);

    AddressPtrList kernel_inputs;
    AddressPtrList kernel_workspaces;
    AddressPtrList kernel_outputs;
    GenLaunchArgs(*kernel_mod, kernel, &kernel_inputs, &kernel_workspaces, &kernel_outputs);
    auto ret = kernel_mod->Launch(kernel_inputs, kernel_workspaces, kernel_outputs, stream_);
    if (!ret) {
      MS_LOG(ERROR) << "Launch kernel failed.";
      return false;
    }
  }
  return true;
}

bool KernelRuntime::LaunchKernel(const session::KernelGraph *graph) {
  MS_EXCEPTION_IF_NULL(graph);
  if (!LaunchKernelMod(*graph)) {
    MS_LOG(ERROR) << "LaunchKernelMod failed!";
    return false;
  }
  if (!SyncStream()) {
    MS_LOG(ERROR) << "SyncStream failed!";
    return false;
  }
  return true;
}

void KernelRuntime::ClearGraphRuntimeResource(uint32_t graph_id) {
  MS_LOG(INFO) << "Clear graph:" << graph_id << " runtime resource";
}

#ifdef ENABLE_DUMP_E2E
bool KernelRuntime::SetDumpConf() {
  dump_conf_ptr_ = std::make_shared<Dump>();
  MS_EXCEPTION_IF_NULL(dump_conf_ptr_);
  bool ret = dump_conf_ptr_->SetDumpConfFromJsonFile();
  return ret;
}

DumpConfPtr KernelRuntime::GetDumpConf() { return dump_conf_ptr_; }
#endif
}  // namespace device
}  // namespace mindspore
