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

#ifndef MINDSPORE_CCSRC_KERNEL_OPLIB_OPINFO_H_
#define MINDSPORE_CCSRC_KERNEL_OPLIB_OPINFO_H_
#include <vector>
#include <string>
#include <memory>
#include <unordered_map>
#include "ir/dtype.h"
#include "kernel/kernel.h"

namespace mindspore {
namespace kernel {
enum OpImplyType { kAKG = 0, kTBE = 1, kAICPU };
enum OpIOType { kInput = 0, kOutput };

class OpAttr {
 public:
  OpAttr() = default;
  ~OpAttr() = default;

  std::string name() const { return name_; }
  std::string param_type() const { return param_type_; }
  std::string type() const { return type_; }
  std::string value() const { return value_; }
  std::string default_value() const { return default_value_; }

  void set_name(const std::string &name) { name_ = name; }
  void set_param_type(const std::string &param_type) { param_type_ = param_type; }
  void set_type(const std::string &type) { type_ = type; }
  void set_value(const std::string &value) { value_ = value; }
  void set_default_value(const std::string &default_value) { default_value_ = default_value; }

 private:
  std::string name_;
  std::string param_type_;
  std::string type_;
  std::string value_;
  std::string default_value_;
};

class OpIOInfo {
 public:
  OpIOInfo() = default;
  ~OpIOInfo() = default;

  int index() const { return index_; }
  std::string name() const { return name_; }
  bool need_compile() const { return need_compile_; }
  std::string param_type() const { return param_type_; }
  std::string reshape_type() const { return reshape_type_; }
  std::string shape() const { return shape_; }
  std::vector<std::string> dtypes() const { return dtypes_; }
  std::vector<std::string> formats() const { return formats_; }

  void set_index(const int index) { index_ = index; }
  void set_name(const std::string &name) { name_ = name; }
  void set_need_compile(const bool need_compile) { need_compile_ = need_compile; }
  void set_param_type(const std::string &param_type) { param_type_ = param_type; }
  void set_reshape_type(const std::string &reshape_type) { reshape_type_ = reshape_type; }
  void set_shape(const std::string &shape) { shape_ = shape; }
  void set_dtypes(const std::vector<std::string> &dtype) { dtypes_ = dtype; }
  void set_formats(const std::vector<std::string> &formats) { formats_ = formats; }

 private:
  int index_ = 0;
  std::string name_;
  bool need_compile_ = false;
  std::string param_type_;
  std::string reshape_type_;
  std::string shape_;
  std::vector<std::string> dtypes_;
  std::vector<std::string> formats_;
};

class OpInfo {
 public:
  OpInfo() = default;
  ~OpInfo() = default;
  std::string op_name() const { return op_name_; }
  OpImplyType imply_type() const { return imply_type_; }
  std::string impl_path() const { return impl_path_; }
  std::string fusion_type() const { return fusion_type_; }
  bool async_flag() const { return async_flag_; }
  std::string binfile_name() const { return binfile_name_; }
  int compute_cost() const { return compute_cost_; }
  std::string kernel_name() const { return kernel_name_; }
  bool partial_flag() const { return partial_flag_; }
  bool dynamic_format() const { return dynamic_format_; }
  OpPattern op_pattern() const { return op_pattern_; }
  std::vector<std::shared_ptr<OpAttr>> attrs_ptr() const { return attrs_ptr_; }
  std::vector<std::shared_ptr<OpIOInfo>> inputs_ptr() const { return inputs_ptr_; }
  std::vector<std::shared_ptr<OpIOInfo>> outputs_ptr() const { return outputs_ptr_; }
  const std::unordered_map<size_t, size_t> &ref_infos() const { return ref_infos_; }

  void set_op_name(const std::string &op_name) { op_name_ = op_name; }
  void set_imply_type(const OpImplyType imply_type) { imply_type_ = imply_type; }
  void set_impl_path(const std::string &impl_path) { impl_path_ = impl_path; }
  void set_fusion_type(const std::string &fusion_type) { fusion_type_ = fusion_type; }
  void set_async_flag(const bool async_flag) { async_flag_ = async_flag; }
  void set_binfile_name(const std::string &binfile_name) { binfile_name_ = binfile_name; }
  void set_compute_cost(const int compute_cost) { compute_cost_ = compute_cost; }
  void set_kernel_name(const std::string &kernel_name) { kernel_name_ = kernel_name; }
  void set_partial_flag(const bool partial_flag) { partial_flag_ = partial_flag; }
  void set_dynamic_format(const bool dynamic_format) { dynamic_format_ = dynamic_format; }
  void set_op_pattern(const OpPattern op_pattern) { op_pattern_ = op_pattern; }
  void add_attrs_ptr(const std::shared_ptr<OpAttr> &attr) { attrs_ptr_.push_back(attr); }
  void add_inputs_ptr(const std::shared_ptr<OpIOInfo> &input) { inputs_ptr_.push_back(input); }
  void add_outputs_ptr(const std::shared_ptr<OpIOInfo> &output) { outputs_ptr_.push_back(output); }
  void set_inputs_ptr(const std::vector<std::shared_ptr<OpIOInfo>> &inputs) { inputs_ptr_ = inputs; }
  void set_outputs_ptr(const std::vector<std::shared_ptr<OpIOInfo>> &outputs) { outputs_ptr_ = outputs; }
  bool is_ref() const { return !ref_infos_.empty(); }
  bool has_ref_index(size_t out_index) const { return ref_infos_.find(out_index) != ref_infos_.end(); }
  void add_ref_pair(size_t out_index, size_t in_index) { (void)ref_infos_.emplace(out_index, in_index); }

 private:
  std::string op_name_;
  OpImplyType imply_type_ = kTBE;
  std::string impl_path_;
  std::string fusion_type_;
  bool async_flag_ = false;
  std::string binfile_name_;
  int compute_cost_ = 0;
  std::string kernel_name_;
  bool partial_flag_ = false;
  bool dynamic_format_ = false;
  OpPattern op_pattern_ = kCommonPattern;
  std::vector<std::shared_ptr<OpAttr>> attrs_ptr_;
  std::vector<std::shared_ptr<OpIOInfo>> inputs_ptr_;
  std::vector<std::shared_ptr<OpIOInfo>> outputs_ptr_;
  std::unordered_map<size_t, size_t> ref_infos_;
};
}  // namespace kernel
}  // namespace mindspore
#endif  // MINDSPORE_CCSRC_KERNEL_OPLIB_OPINFO_H_
