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

#include "operator/ops.h"
#include <memory>
#include <string>
#include "pipeline/parse/python_adapter.h"
#include "pipeline/parse/data_converter.h"

namespace mindspore {
// namespace to support primitive operators
namespace prim {
ValuePtr GetPythonOps(const std::string &op_name, const std::string &module_name) {
  py::object obj = parse::python_adapter::GetPyFn(module_name, op_name);
  ValuePtr node = nullptr;
  bool succ = parse::ConvertData(obj, &node);
  if (!succ) {
    MS_LOG(EXCEPTION) << "get Python op " << op_name << " from " << module_name << " fail";
  }
  return node;
}
}  // namespace prim
}  // namespace mindspore
