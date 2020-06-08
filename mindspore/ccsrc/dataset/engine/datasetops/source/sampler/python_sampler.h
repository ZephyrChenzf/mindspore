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
#ifndef DATASET_ENGINE_DATASETOPS_SOURCE_SAMPLER_PYTHON_SAMPLER_H_
#define DATASET_ENGINE_DATASETOPS_SOURCE_SAMPLER_PYTHON_SAMPLER_H_

#include <limits>
#include <memory>

#include "dataset/engine/datasetops/source/sampler/sampler.h"

namespace mindspore {
namespace dataset {
class PythonSampler : public Sampler {
 public:
  // Constructor
  // @param num_samples - the number of samples to draw.  Value of 0 means to sample all of the
  //                      data from the dataset.
  // @param py_sampler_instance - the python instance of the sampler
  // @param int64_t samples_per_buffer - Num of Sampler Ids to fetch via 1 GetNextBuffer call
  explicit PythonSampler(int64_t num_samples, py::object py_sampler_instance,
                         int64_t samples_per_buffer = std::numeric_limits<int64_t>::max());

  // Destructor.
  ~PythonSampler() = default;

  // Initialize the sampler.
  // @return Status
  Status InitSampler() override;

  // for next epoch of sampleIds
  // @return - The error code return
  Status Reset() override;

  // Op calls this to get next Buffer that contains all the sampleIds
  // @param std::unique_ptr<DataBuffer> pBuffer - Buffer to be returned to StorageOp
  // @param int32_t workerId - not meant to be used
  // @return - The error code return
  Status GetNextBuffer(std::unique_ptr<DataBuffer> *out_buffer) override;

 private:
  bool need_to_reset_;  // Whether Reset() should be called before calling GetNextBuffer()

  py::object py_sampler_instance;  // The handle to the py_sampler python object
};
}  // namespace dataset
}  // namespace mindspore

#endif  // DATASET_ENGINE_DATASETOPS_SOURCE_SAMPLER_PYTHON_SAMPLER_H_
