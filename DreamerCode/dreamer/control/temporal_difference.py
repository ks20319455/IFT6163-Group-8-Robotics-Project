# Copyright 2019 The Dreamer Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf


def discounted_return(reward, pcont, bootstrap, axis, stop_gradient=True):
  if isinstance(pcont, (float, int)):
    if pcont == 1 and bootstrap is None:
      return tf.reduce_sum(reward, axis)
    if pcont == 1:
      return tf.reduce_sum(reward, axis) + bootstrap
    pcont = pcont * tf.ones_like(reward)
  # Bring the aggregation dimension front.
  dims = list(range(reward.shape.ndims))
  dims = [axis] + dims[1:axis] + [0] + dims[axis + 1:]
  reward = tf.transpose(reward, dims)
  pcont = tf.transpose(pcont, dims)
  if bootstrap is None:
    bootstrap = tf.zeros_like(reward[-1])
  return_ = tf.scan(
      fn=lambda agg, cur: cur[0] + cur[1] * agg,
      elems=(reward, pcont),
      initializer=bootstrap,
      back_prop=not stop_gradient,
      reverse=True)
  return_ = tf.transpose(return_, dims)
  if stop_gradient:
    return_ = tf.stop_gradient(return_)
  return return_


def lambda_return(
    reward, value, bootstrap, pcont, lambda_, axis, stop_gradient=True):
  # Setting lambda=1 gives a discounted Monte Carlo return.
  # Setting lambda=0 gives a fixed 1-step return.
  assert reward.shape.ndims == value.shape.ndims, (reward.shape, value.shape)
  # Bring the aggregation dimension front.
  dims = list(range(reward.shape.ndims))
  dims = [axis] + dims[1:axis] + [0] + dims[axis + 1:]
  if isinstance(pcont, (int, float)):
    pcont = pcont * tf.ones_like(reward)
  reward = tf.transpose(reward, dims)
  value = tf.transpose(value, dims)
  pcont = tf.transpose(pcont, dims)
  if bootstrap is None:
    bootstrap = tf.zeros_like(value[-1])
  next_values = tf.concat([value[1:], bootstrap[None]], 0)
  inputs = reward + pcont * next_values * (1 - lambda_)
  return_ = tf.scan(
      fn=lambda agg, cur: cur[0] + cur[1] * lambda_ * agg,
      elems=(inputs, pcont),
      initializer=bootstrap,
      back_prop=not stop_gradient,
      reverse=True)
  return_ = tf.transpose(return_, dims)
  if stop_gradient:
    return_ = tf.stop_gradient(return_)
  return return_


def fixed_step_return(
    reward, value, discount, steps, axis, stop_gradient=True):
  # Brings the aggregation dimension front.
  dims = list(range(reward.shape.ndims))
  dims = [axis] + dims[1:axis] + [0] + dims[axis + 1:]
  reward = tf.transpose(reward, dims)
  length = tf.shape(reward)[0]
  _, return_ = tf.while_loop(
      cond=lambda i, p: i < steps + 1,
      body=lambda i, p: (i + 1, reward[steps - i: length - i] + discount * p),
      loop_vars=[tf.constant(1), tf.zeros_like(reward[steps:])],
      back_prop=not stop_gradient)
  if value is not None:
    return_ += discount ** steps * tf.transpose(value, dims)[steps:]
  return_ = tf.transpose(return_, dims)
  if stop_gradient:
    return_ = tf.stop_gradient(return_)
  return return_
