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
#ifndef DATASET_ENGINE_DATASETOPS_SOURCE_SAMPLER_SAMPLER_H_
#define DATASET_ENGINE_DATASETOPS_SOURCE_SAMPLER_SAMPLER_H_

#include <limits>
#include <map>
#include <memory>
#include <random>
#include <vector>

#include "dataset/core/tensor.h"
#include "dataset/engine/data_buffer.h"
#include "dataset/engine/data_schema.h"
#include "dataset/engine/datasetops/dataset_op.h"

namespace mindspore {
namespace dataset {
//  RandomAccessOp is a base class that all data-producing leaf operators
//  must inherit from if those leaf operator wish to support sampling.
class RandomAccessOp {
 public:
  // Sampler get number of rows in the dataset
  // @param int64_t num - return number of rows for this dataset
  // @return - The error code return
  Status GetNumRowsInDataset(int64_t *num_rows) const;

  // sampler gets label , imageIds from storageOp, this function is unique to PK
  // @param std::map<int64_t, std::vector<int64_t>> * map
  // @return - The error code return
  virtual Status GetClassIds(std::map<int32_t, std::vector<int64_t>> *map) const {
    RETURN_STATUS_UNEXPECTED("GetClassIds needs to be override to support PK");
  }

  // default destructor
  virtual ~RandomAccessOp() = default;

 protected:
  // The amount of rows in the dataset itself. This is the before-sampling value, the
  // total count of rows.  A sampler may choose to sample less than this amount.
  int64_t num_rows_;
};

class Sampler : public DatasetOp {
 public:
  // Constructor
  // @param int64_t num_samples: the user-requested number of samples ids to generate. A value of 0
  //                indicates that the sampler should produce the complete set of ids.
  // @param int64_t samplesPerBuffer: Num of Sampler Ids to fetch via 1 GetNextBuffer call
  explicit Sampler(int64_t num_samples, int64_t samples_per_buffer);

  // default destructor
  ~Sampler() = default;

  // Get a list of sample ids.
  // @note It is Sampler responsibility to make sure that the id is not out of bound.
  // @param std::unique_ptr<DataBuffer> pBuffer - Buffer to be returned to StorageOp
  // @param int32_t workerId - not meant to be used
  // @return - The error code return
  Status GetNextBuffer(std::unique_ptr<DataBuffer> *out_buffer) override = 0;

  // return all ids in one epoch as a numpy array, then call reset
  Status GetAllIdsThenReset(py::array *data);

  // for next epoch of sampleIds
  // @return - The error code return
  Status Reset() override = 0;

  // first handshake between leaf source op and Sampler. This func will determine the amount of data
  // in the dataset that we can sample from.
  // @param op - leaf op pointer, pass in so Sampler can ask it about how much data there is
  // @return
  virtual Status HandshakeRandomAccessOp(const RandomAccessOp *op);

  // initialize sampler and perform checks on certain vars
  virtual Status InitSampler() { return Status::OK(); }

  // setter for num samples
  // @param num_samples - the number of samples to assign.
  // @return status error code
  Status SetNumSamples(int64_t num_samples);

  // setter for num or records in the dataset
  // @param num_rows - the number of records
  // @return status error code
  Status SetNumRowsInDataset(int64_t num_rows);

  // Sampler is an inlined op and has no workers.  Producers and consumers are computed.
  // @return
  int32_t num_workers() const final { return 0; }

  // Identify num consumers (inlined op)
  // @return
  int32_t num_consumers() const final;

  // Identify num producers (inlined op)
  // @return
  int32_t num_producers() const final;

  // Not meant to be called!
  // @return - The error code return
  Status operator()() final { RETURN_STATUS_UNEXPECTED("Functor not supported in Sampler"); }

  // Adds a sampler to become our child.
  // @param std::shared_ptr<DatasetOp> - The sampler to add as a child.
  // @return - The error code returned.
  Status AddChild(std::shared_ptr<DatasetOp> child);

  // A helper function to create a int64_t 1-D Tensor specifically used to hold sampleIds for Sampler
  // @param std::shared_ptr<Tensor>* sampleIds
  // @param int64_t numElements - must be a non 0 number
  // @return - The error code returned.
  Status CreateSamplerTensor(std::shared_ptr<Tensor> *sample_ids, int64_t num_elements);

  void Print(std::ostream &out, bool show_all) const override;

  friend std::ostream &operator<<(std::ostream &out, const Sampler &sampler) {
    sampler.Print(out, false);
    return out;
  }

  // Checks if this sampler has a child sampler.
  // @return - tre if there is a child sampler, false otherwise.
  bool HasChildSampler();

  // Uses id as an index for the list of ids generated by the child sampler, and gets the
  // associated id.
  // @param int64_t* out_associated_id - Out parameter, contains the associated id.
  // @param int64_t id - The id used as an index to get the associated child id.
  // @return - The error code returned.
  Status GetAssociatedChildId(int64_t *out_associated_id, int64_t id);

 protected:
  // Number of rows of data from the place this sampler is sampling from. If this sampler
  // has a child sampler, num_rows_ is the number of ids the child sampler will
  // output. Otherwise, num_rows_ is the number of rows in the dataset.
  int64_t num_rows_;

  // The user may want to sample less than the full amount of data.  num_samples_ reduces the number
  // of id's returned as request by the user.  Derived classes will choose how to sample the smaller
  // amount.
  int64_t num_samples_;

  int64_t samples_per_buffer_;
  std::unique_ptr<ColDescriptor> col_desc_;
  std::unique_ptr<DataBuffer> child_ids_;
};
}  // namespace dataset
}  // namespace mindspore

#endif  // DATASET_ENGINE_DATASETOPS_SOURCE_SAMPLER_SAMPLER_H_
