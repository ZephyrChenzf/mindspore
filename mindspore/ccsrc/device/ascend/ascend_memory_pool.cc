/**
 * Copyright 2020 Huawei Technologies Co., Ltd
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

#include "device/ascend/ascend_memory_pool.h"
#include "device/ascend/ascend_kernel_runtime.h"
#include "utils/log_adapter.h"

namespace mindspore {
namespace device {
namespace ascend {
size_t AscendMemoryPool::AllocDeviceMem(size_t size, DeviceMemPtr *addr) {
  if (has_malloc_) {
    MS_LOG(EXCEPTION) << "Has alloc memory pool memory !";
  }
  if (size == 0 || size > free_mem_size_) {
    MS_LOG(EXCEPTION) << "Failed to alloc memory pool memory !";
  }
  *addr = device_mem_pool_base_;
  if (*addr == nullptr) {
    MS_LOG(EXCEPTION) << "Device memory pool base is nullptr, failed to alloc memory pool memory!";
  }
  has_malloc_ = true;
  free_mem_size_ -= size;
  return size;
}

bool AscendMemoryPool::FreeDeviceMem(const DeviceMemPtr &addr) {
  MS_EXCEPTION_IF_NULL(addr);
  has_malloc_ = false;
  free_mem_size_ = total_mem_size_;
  return true;
}

size_t AscendMemoryPool::AlignMemorySize(size_t size) const {
  if (size == 0) {
    return DYNAMIC_MEM_ALIGN_SIZE;
  }
  return ((size + DYNAMIC_MEM_ALIGN_SIZE + 31) / DYNAMIC_MEM_ALIGN_SIZE) * DYNAMIC_MEM_ALIGN_SIZE;
}

size_t AscendMemoryPool::mem_alloc_unit_size() const { return free_mem_size_ - 512; }

void AscendMemoryPool::set_device_mem_pool_base(uint8_t *device_mem_pool_base) {
  MS_EXCEPTION_IF_NULL(device_mem_pool_base);
  device_mem_pool_base_ = device_mem_pool_base;
}

size_t AscendMemoryPool::free_mem_size() { return free_mem_size_; }

size_t AscendMemoryPool::total_mem_size() { return total_mem_size_; }
}  // namespace ascend
}  // namespace device
}  // namespace mindspore
