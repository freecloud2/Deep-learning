# Copyright 2017 The Sonnet Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or  implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

"""Tests for snt.nets.alexnet."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools
# Dependency imports
from absl.testing import parameterized
import numpy as np

import sonnet as snt

import tensorflow.compat.v1 as tf
from tensorflow.contrib import layers as contrib_layers
from tensorflow.contrib.eager.python import tfe as contrib_eager
from tensorflow.python.ops import variables


@contrib_eager.run_all_tests_in_graph_and_eager_modes
class AlexNetTest(parameterized.TestCase, tf.test.TestCase):

  def testCalcMinSize(self):
    """Test the minimum input size calculator."""
    net = snt.nets.AlexNetMini()

    self.assertEqual(net._calc_min_size([(None, (3, 1), None)]), 3)
    self.assertEqual(net._calc_min_size([(None, (3, 1), (3, 2))]), 5)
    self.assertEqual(net._calc_min_size([(None, (3, 1), (3, 2)),
                                         (None, (3, 2), (5, 2))]), 25)

  @parameterized.named_parameters(
      ("full", functools.partial(snt.nets.AlexNet, mode=snt.nets.AlexNet.FULL)),
      ("mini", functools.partial(snt.nets.AlexNet, mode=snt.nets.AlexNet.MINI)),
      ("full_module", snt.nets.AlexNetFull),
      ("mini_module", snt.nets.AlexNetMini),
  )
  def testModes(self, module):
    """Test that each mode can be instantiated."""
    keep_prob = 0.7
    net = module()
    input_shape = [1, net._min_size, net._min_size, 3]
    inputs = tf.ones(dtype=tf.float32, shape=input_shape)
    net(inputs, keep_prob, is_training=True)

  @parameterized.named_parameters(
      ("all_layers", True),
      ("conv_only", False))
  def testBatchNorm(self, bn_on_fc_layers):
    """Test that batch norm can be instantiated."""

    net = snt.nets.AlexNet(
        mode=snt.nets.AlexNet.FULL,
        use_batch_norm=True,
        bn_on_fc_layers=bn_on_fc_layers)
    input_shape = [net._min_size, net._min_size, 3]
    inputs = tf.ones(dtype=tf.float32, shape=[1] + input_shape)
    output = net(inputs, is_training=True)

    self.evaluate(tf.global_variables_initializer())
    self.evaluate(output)

    # Check that an error is raised if we don't specify the is_training flag
    err = "is_training flag must be explicitly specified"
    with self.assertRaisesRegexp(ValueError, err):
      net(inputs)

    # Check Tensorflow flags work
    is_training = tf.constant(False)
    test_local_stats = tf.constant(False)
    net(inputs,
        is_training=is_training,
        test_local_stats=test_local_stats)

    # Check Python is_training flag works
    net(inputs, is_training=False, test_local_stats=False)

    # Check that the appropriate moving statistics variables have been created.
    variance_name = "alex_net/batch_norm/moving_variance:0"
    mean_name = "alex_net/batch_norm/moving_mean:0"
    var_names = [var.name for var in tf.global_variables()]
    self.assertIn(variance_name, var_names)
    self.assertIn(mean_name, var_names)
    if bn_on_fc_layers:
      self.assertEqual(35, len(var_names))
    else:
      self.assertEqual(29, len(var_names))

  def testBatchNormConfig(self):
    batch_norm_config = {
        "scale": True,
    }

    model = snt.nets.AlexNetFull(use_batch_norm=True,
                                 batch_norm_config=batch_norm_config)

    input_to_net = tf.ones(dtype=tf.float32, shape=(1, 224, 224, 3))

    model(input_to_net, is_training=True)
    model_variables = model.get_variables()

    self.assertEqual(len(model_variables), 6 * 4)

  def testNoDropoutInTesting(self):
    """An exception should be raised if trying to use dropout when testing."""
    net = snt.nets.AlexNetFull()
    input_shape = [net._min_size, net._min_size, 3]
    inputs = tf.ones(dtype=tf.float32, shape=[1] + input_shape)

    with self.assertRaisesRegexp(tf.errors.InvalidArgumentError, "keep_prob"):
      output = net(inputs, keep_prob=0.7, is_training=False)
      self.evaluate(tf.global_variables_initializer())
      self.evaluate(output)

    # No exception if keep_prob=1
    output = net(inputs, keep_prob=1.0, is_training=False)
    self.evaluate(output)

  def testInputTooSmall(self):
    """Check that an error is raised if the input image is too small."""

    keep_prob = 0.7
    net = snt.nets.AlexNetFull()

    input_shape = [1, net._min_size, net._min_size, 1]
    inputs = tf.ones(dtype=tf.float32, shape=input_shape)
    net(inputs, keep_prob, is_training=True)

    with self.assertRaisesRegexp(snt.IncompatibleShapeError,
                                 "Image shape too small: (.*?, .*?) < .*?"):
      input_shape = [1, net._min_size - 1, net._min_size - 1, 1]
      inputs = tf.ones(dtype=tf.float32, shape=input_shape)
      net(inputs, keep_prob, is_training=True)

  def testSharing(self):
    """Check that the correct number of variables are made when sharing."""

    net = snt.nets.AlexNetMini()
    inputs1 = tf.ones(dtype=tf.float32, shape=[1, 64, 64, 3])
    inputs2 = tf.ones(dtype=tf.float32, shape=[1, 64, 64, 3])
    keep_prob1 = 0.7
    keep_prob2 = 0.5

    net(inputs1, keep_prob1, is_training=True)
    net(inputs2, keep_prob2, is_training=True)

    self.assertLen(tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES),
                   7 * 2)

    model_variables = net.get_variables()
    self.assertEqual(len(model_variables), 7 * 2)

  def testInvalidInitializationParameters(self):
    err = "Invalid initializer keys.*"
    with self.assertRaisesRegexp(KeyError, err):
      snt.nets.AlexNetMini(
          initializers={"not_w": tf.truncated_normal_initializer(stddev=1.0)})

    err = "Initializer for 'w' is not a callable function"
    with self.assertRaisesRegexp(TypeError, err):
      snt.nets.AlexNetMini(
          initializers={"w": tf.zeros([1, 2, 3])})

  def testInvalidRegularizationParameters(self):
    with self.assertRaisesRegexp(KeyError, "Invalid regularizer keys.*"):
      snt.nets.AlexNetMini(
          regularizers={"not_w": contrib_layers.l1_regularizer(scale=0.5)})

    err = "Regularizer for 'w' is not a callable function"
    with self.assertRaisesRegexp(TypeError, err):
      snt.nets.AlexNetMini(
          regularizers={"w": tf.zeros([1, 2, 3])})

  def testRegularizersInRegularizationLosses(self):
    regularizers = {
        "w": contrib_layers.l1_regularizer(scale=0.5),
        "b": contrib_layers.l2_regularizer(scale=0.5)
    }

    alex_net = snt.nets.AlexNetMini(
        regularizers=regularizers, name="alexnet1")

    input_shape = [alex_net._min_size, alex_net._min_size, 3]
    inputs = tf.ones(dtype=tf.float32, shape=[1] + input_shape)
    alex_net(inputs)

    graph_regularizers = tf.get_collection(
        tf.GraphKeys.REGULARIZATION_LOSSES)

    alex_net_conv_layers = len(alex_net.conv_modules)
    self.assertEqual(len(graph_regularizers), 2 * alex_net_conv_layers)

  def testInitializers(self):
    initializers = {
        "w": tf.constant_initializer(1.5),
        "b": tf.constant_initializer(2.5),
    }
    alex_net = snt.nets.AlexNetFull(initializers=initializers)
    input_shape = [1, alex_net.min_input_size, alex_net.min_input_size, 3]
    inputs = tf.ones(dtype=tf.float32, shape=input_shape)
    alex_net(inputs)
    init = tf.global_variables_initializer()

    self.evaluate(init)
    for module in alex_net.conv_modules + alex_net.linear_modules:
      w_v, b_v = self.evaluate([module.w, module.b])
      self.assertAllClose(w_v, 1.5 * np.ones(w_v.shape))
      self.assertAllClose(b_v, 2.5 * np.ones(b_v.shape))

  def testPartitioners(self):
    if tf.executing_eagerly():
      self.skipTest("Eager does not support partitioned variables.")

    partitioners = {
        "w": tf.fixed_size_partitioner(num_shards=2),
        "b": tf.fixed_size_partitioner(num_shards=2),
    }

    alex_net = snt.nets.AlexNetMini(
        partitioners=partitioners, name="alexnet1")

    input_shape = [alex_net._min_size, alex_net._min_size, 3]
    inputs = tf.placeholder(tf.float32, shape=[None] + input_shape)
    alex_net(inputs)

    for conv_module in alex_net.conv_modules:
      self.assertEqual(type(conv_module.w), variables.PartitionedVariable)
      self.assertEqual(type(conv_module.b), variables.PartitionedVariable)

    for linear_module in alex_net.linear_modules:
      self.assertEqual(type(linear_module.w), variables.PartitionedVariable)
      self.assertEqual(type(linear_module.b), variables.PartitionedVariable)

  def testErrorHandling(self):
    err = "AlexNet construction mode 'BLAH' not recognised"
    with self.assertRaisesRegexp(snt.Error, err):
      snt.nets.AlexNet(mode="BLAH")

  def testGetLinearModules(self):
    alex_net = snt.nets.AlexNetFull()
    input_shape = [1, alex_net.min_input_size, alex_net.min_input_size, 3]
    inputs = tf.ones(dtype=tf.float32, shape=input_shape)
    alex_net(inputs)
    for mod in alex_net.linear_modules:
      self.assertEqual(mod.output_size, 4096)

  def testCustomGetterUsed(self):

    const = 42.

    def set_to_const(getter, *args, **kwargs):
      variable = getter(*args, **kwargs)
      return 0.0 * variable + const

    alex_net = snt.nets.AlexNetFull(custom_getter=set_to_const)
    input_shape = [1, alex_net.min_input_size, alex_net.min_input_size, 3]
    inputs = tf.ones(dtype=tf.float32, shape=input_shape)
    alex_net(inputs)

    self.evaluate(tf.global_variables_initializer())
    for module in alex_net.conv_modules + alex_net.linear_modules:
      var_w, var_b = self.evaluate([module.w, module.b])
      self.assertAllClose(var_w, np.zeros_like(var_w) + const)
      self.assertAllClose(var_b, np.zeros_like(var_b) + const)


if __name__ == "__main__":
  tf.test.main()
