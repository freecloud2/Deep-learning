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

"""Test sonnet.python.modules.nets.convnet."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import functools
import itertools
# Dependency imports

from absl.testing import parameterized
import numpy as np
import sonnet as snt
from sonnet.python.modules.conv import _fill_shape as fill_shape

import tensorflow.compat.v1 as tf
from tensorflow.contrib import layers as contrib_layers
from tensorflow.contrib.eager.python import tfe as contrib_eager
from tensorflow.python.ops import variables  # pylint: disable=g-direct-tensorflow-import


@contrib_eager.run_all_tests_in_graph_and_eager_modes
class SharedConvNets2DTest(parameterized.TestCase, tf.test.TestCase):

  def setUp(self):
    super(SharedConvNets2DTest, self).setUp()
    self.output_channels = [2, 3, 4]
    self.kernel_shapes = [[3, 3]]
    self.strides = [1]
    self.rates = [1, 2, 1]
    self.paddings = [snt.SAME]

  @parameterized.named_parameters(
      ("ConvNet2D", snt.nets.ConvNet2D),
      ("ConvNet2DTranspose", functools.partial(snt.nets.ConvNet2DTranspose,
                                               output_shapes=[[100, 100]])))
  def testName(self, module):
    unique_name = "unique_name"
    with tf.variable_scope("scope"):
      net = module(name=unique_name,
                   output_channels=self.output_channels,
                   kernel_shapes=self.kernel_shapes,
                   strides=self.strides,
                   paddings=self.paddings)
    self.assertEqual(net.scope_name, "scope/" + unique_name)
    self.assertEqual(net.module_name, unique_name)

  @parameterized.named_parameters(
      ("ConvNet2D", snt.nets.ConvNet2D),
      ("ConvNet2DTranspose", functools.partial(snt.nets.ConvNet2DTranspose,
                                               output_shapes=[[100, 100]])))
  def testConstructor(self, module):
    with self.assertRaisesRegexp(ValueError,
                                 "output_channels must not be empty"):
      module(output_channels=[],
             kernel_shapes=self.kernel_shapes,
             strides=self.strides,
             paddings=self.paddings)

    with self.assertRaisesRegexp(ValueError,
                                 "kernel_shapes must be of length 1 or *"):
      module(output_channels=self.output_channels,
             kernel_shapes=[],
             strides=self.strides,
             paddings=self.paddings)

    with self.assertRaisesRegexp(ValueError,
                                 "kernel_shapes must be of length 1 or *"):
      module(output_channels=self.output_channels,
             kernel_shapes=[1, 2],
             strides=self.strides,
             paddings=self.paddings)

    with self.assertRaisesRegexp(ValueError,
                                 "strides must be of length 1 or *"):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=[],
             paddings=self.paddings)

    with self.assertRaisesRegexp(ValueError,
                                 "strides must be of length 1 or *"):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=[1, 1],
             paddings=self.paddings)

    with self.assertRaisesRegexp(ValueError,
                                 "paddings must be of length 1 or *"):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=self.paddings,
             paddings=[])

    with self.assertRaisesRegexp(ValueError,
                                 "paddings must be of length 1 or *"):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=self.strides,
             paddings=[snt.SAME, snt.SAME])

    with self.assertRaisesRegexp(KeyError,
                                 "Invalid initializer keys.*"):
      module(
          output_channels=self.output_channels,
          kernel_shapes=self.kernel_shapes,
          strides=self.strides,
          paddings=self.paddings,
          initializers={"not_w": tf.truncated_normal_initializer(stddev=1.0)})

    with self.assertRaisesRegexp(TypeError,
                                 "Initializer for 'w' is not a callable "
                                 "function or dictionary"):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=self.strides,
             paddings=self.paddings,
             initializers={"w": tf.zeros([1, 2, 3])})

    with self.assertRaisesRegexp(KeyError,
                                 "Invalid regularizer keys.*"):
      module(
          output_channels=self.output_channels,
          kernel_shapes=self.kernel_shapes,
          strides=self.strides,
          paddings=self.paddings,
          regularizers={"not_w": contrib_layers.l1_regularizer(scale=0.5)})

    with self.assertRaisesRegexp(TypeError,
                                 "Regularizer for 'w' is not a callable "
                                 "function or dictionary"):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=self.strides,
             paddings=self.paddings,
             regularizers={"w": tf.zeros([1, 2, 3])})

    with self.assertRaisesRegexp(TypeError,
                                 "Input 'activation' must be callable"):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=self.strides,
             paddings=self.paddings,
             activation="not_a_function")

    err = "output_channels must be iterable"
    with self.assertRaisesRegexp(TypeError, err):
      module(output_channels=42,
             kernel_shapes=self.kernel_shapes,
             strides=self.strides,
             paddings=self.paddings)

    err = "kernel_shapes must be iterable"
    with self.assertRaisesRegexp(TypeError, err):
      module(output_channels=self.output_channels,
             kernel_shapes=None,
             strides=self.strides,
             paddings=self.paddings)

    err = "strides must be iterable"
    with self.assertRaisesRegexp(TypeError, err):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=True,
             paddings=self.paddings)

    err = "paddings must be iterable"
    with self.assertRaisesRegexp(TypeError, err):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=self.strides,
             paddings=lambda x: x + 42)

    err = "use_bias must be either a bool or an iterable"
    with self.assertRaisesRegexp(TypeError, err):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=self.strides,
             paddings=self.paddings,
             use_bias=2)

    err = "use_batch_norm must be a boolean"
    with self.assertRaisesRegexp(TypeError, err):
      module(output_channels=self.output_channels,
             kernel_shapes=self.kernel_shapes,
             strides=self.strides,
             paddings=self.paddings,
             use_batch_norm=[True])

    err = "Invalid data_format"
    # Also checks that the error works with non-string types
    for data_format in ["NHCW", 3]:
      with self.assertRaisesRegexp(ValueError, err):
        module(
            output_channels=self.output_channels,
            kernel_shapes=self.kernel_shapes,
            strides=self.strides,
            paddings=self.paddings,
            data_format=data_format)

  @parameterized.named_parameters(
      ("ConvNet2D", snt.nets.ConvNet2D),
      ("ConvNet2DTranspose",
       functools.partial(snt.nets.ConvNet2DTranspose,
                         output_shapes=[[100, 100]])))
  def testBatchNormBuildFlag(self, module):
    model = module(output_channels=self.output_channels,
                   kernel_shapes=self.kernel_shapes,
                   strides=self.strides,
                   paddings=self.paddings,
                   use_batch_norm=True)
    self.assertTrue(model.use_batch_norm)
    input_to_net = tf.random_normal(dtype=tf.float32, shape=(1, 100, 100, 3))

    # Check that an error is raised if we don't specify the is_training flag
    err = "is_training flag must be explicitly specified"
    with self.assertRaisesRegexp(ValueError, err):
      model(input_to_net)

  @parameterized.named_parameters(
      ("ConvNet2D", snt.nets.ConvNet2D),
      ("ConvNet2DTranspose",
       functools.partial(snt.nets.ConvNet2DTranspose,
                         output_shapes=[[100, 100]])))
  def testBatchNorm(self, module):
    model = module(output_channels=self.output_channels,
                   kernel_shapes=self.kernel_shapes,
                   strides=self.strides,
                   paddings=self.paddings,
                   use_batch_norm=True)
    self.assertTrue(model.use_batch_norm)
    input_to_net = tf.random_normal(dtype=tf.float32, shape=(1, 100, 100, 3))

    # Check Tensorflow flags work
    is_training = tf.constant(False)
    test_local_stats = tf.constant(False)

    model(input_to_net,
          is_training=is_training,
          test_local_stats=test_local_stats)

    # Check Python is_training flag works
    model(input_to_net, is_training=False, test_local_stats=False)

    model_variables = model.get_variables()

    self.assertLen(model_variables, len(self.output_channels) * 3 - 1)

    # Check that the appropriate moving statistics variables have been created.
    self.assertTrue(
        any("moving_variance" in var.name
            for var in tf.global_variables()))
    self.assertTrue(
        any("moving_mean" in var.name
            for var in tf.global_variables()))

  @parameterized.named_parameters(
      ("ConvNet2D", snt.nets.ConvNet2D),
      ("ConvNet2DTranspose", functools.partial(snt.nets.ConvNet2DTranspose,
                                               output_shapes=[[100, 100]])))
  def testBatchNormConfig(self, module):
    batch_norm_config = {
        "scale": True,
    }

    model = module(output_channels=self.output_channels,
                   kernel_shapes=self.kernel_shapes,
                   strides=self.strides,
                   paddings=self.paddings,
                   use_batch_norm=True,
                   batch_norm_config=batch_norm_config)

    input_to_net = tf.random_normal(dtype=tf.float32, shape=(1, 100, 100, 3))

    model(input_to_net, is_training=True)
    model_variables = model.get_variables()

    self.assertLen(model_variables, len(self.output_channels) * 4 - 2)

  @parameterized.named_parameters(
      ("ConvNet2D", snt.nets.ConvNet2D),
      ("ConvNet2DTranspose", functools.partial(snt.nets.ConvNet2DTranspose,
                                               output_shapes=[[100, 100]])))
  def testNoBias(self, module):
    model = module(output_channels=self.output_channels,
                   kernel_shapes=self.kernel_shapes,
                   strides=self.strides,
                   paddings=self.paddings,
                   use_bias=False)
    self.assertEqual(model.use_bias, (False,) * len(self.output_channels))
    input_to_net = tf.random_normal(dtype=tf.float32, shape=(1, 100, 100, 3))
    model(input_to_net)

    model_variables = model.get_variables()

    self.assertLen(model_variables, len(self.output_channels))

  @parameterized.named_parameters(
      ("ConvNet2D", snt.nets.ConvNet2D),
      ("ConvNet2DTranspose", functools.partial(snt.nets.ConvNet2DTranspose,
                                               output_shapes=[[100, 100]])))
  def testNoBiasIterable(self, module):
    use_bias = (True,) * (len(self.output_channels) - 1) + (False,)
    model = module(output_channels=self.output_channels,
                   kernel_shapes=self.kernel_shapes,
                   strides=self.strides,
                   paddings=self.paddings,
                   use_bias=use_bias)

    actual_use_biases = tuple(layer.has_bias for layer in model.layers)
    self.assertEqual(model.use_bias, actual_use_biases)
    self.assertEqual(use_bias, actual_use_biases)

    model_transpose = model.transpose()
    actual_use_biases = tuple(layer.has_bias
                              for layer in model_transpose.layers)
    self.assertEqual(model_transpose.use_bias, actual_use_biases)
    self.assertEqual(tuple(reversed(use_bias)), actual_use_biases)

  @parameterized.named_parameters(("ConvNet2DNoBias", False, False),
                                  ("ConvNet2DBias", False, True),
                                  ("ConvNet2DTransposeNoBias", True, False),
                                  ("ConvNet2DTransposeBias", True, True))
  def testRegularizersInRegularizationLosses(self, transpose, use_bias):
    if transpose:
      module = functools.partial(snt.nets.ConvNet2DTranspose,
                                 output_shapes=[[100, 100]])
    else:
      module = snt.nets.ConvNet2D
    if use_bias:
      regularizers = {
          "w": contrib_layers.l1_regularizer(scale=0.5),
          "b": contrib_layers.l2_regularizer(scale=0.5)
      }
    else:
      regularizers = {"w": contrib_layers.l1_regularizer(scale=0.5)}

    model = module(output_channels=self.output_channels,
                   kernel_shapes=self.kernel_shapes,
                   strides=self.strides,
                   paddings=self.paddings,
                   use_bias=use_bias,
                   regularizers=regularizers)

    input_to_net = tf.random_normal(dtype=tf.float32, shape=(1, 100, 100, 3))
    model(input_to_net)

    regularizers = tf.get_collection(
        tf.GraphKeys.REGULARIZATION_LOSSES)
    expected_num_regularizers = 3 * (2 if use_bias else 1)
    self.assertLen(regularizers, expected_num_regularizers)
    if not tf.executing_eagerly():
      self.assertRegexpMatches(regularizers[0].name, ".*l1_regularizer.*")
      if use_bias:
        self.assertRegexpMatches(regularizers[1].name, ".*l2_regularizer.*")

  @parameterized.named_parameters(
      ("ConvNet2D", snt.nets.ConvNet2D, False),
      ("ConvNet2DFinal", snt.nets.ConvNet2D, True),
      ("ConvNet2DTranspose",
       functools.partial(snt.nets.ConvNet2DTranspose,
                         output_shapes=[[100, 100]]),
       False),
      ("ConvNet2DTransposeFinal",
       functools.partial(snt.nets.ConvNet2DTranspose,
                         output_shapes=[[100, 100]]),
       True))
  def testActivateFinal(self, module, activate_final):
    model = module(output_channels=self.output_channels,
                   kernel_shapes=self.kernel_shapes,
                   strides=self.strides,
                   paddings=self.paddings,
                   activate_final=activate_final,
                   use_batch_norm=True,
                   use_bias=False)
    self.assertEqual(activate_final, model.activate_final)
    input_to_net = tf.random_normal(dtype=tf.float32, shape=(1, 100, 100, 3))
    model(input_to_net, is_training=True)

    model_variables = model.get_variables()

    # Batch norm variable missing for final activation
    if activate_final:
      self.assertLen(model_variables, len(self.output_channels) * 2)
    else:
      self.assertLen(model_variables, len(self.output_channels) * 2 - 1)

    # Test transpose method's activate_final arg.
    transposed_model_activate_final = model.transpose(activate_final=True)
    transposed_model_no_activate_final = model.transpose(activate_final=False)
    transposed_model_inherit_activate_final = model.transpose()
    self.assertEqual(True, transposed_model_activate_final.activate_final)
    self.assertEqual(False, transposed_model_no_activate_final.activate_final)
    self.assertEqual(model.activate_final,
                     transposed_model_inherit_activate_final.activate_final)

  @parameterized.parameters(
      *itertools.product(
          [snt.nets.ConvNet2D,
           functools.partial(snt.nets.ConvNet2DTranspose,
                             output_shapes=[[100, 100]])],
          ["kernel_shapes", "strides", "paddings", "activation", "initializers",
           "partitioners", "regularizers", "use_bias", "batch_norm_config"]))
  def testTransposeDefaultParameter(self, module, param_name):
    """Tests if .transpose correctly chooses the default parameters.

    Args:
      module: The conv net class.
      param_name: The name of the parameter to test.
    """
    # For these parameters, the expected values are their reversed values
    expected_reversed = ["kernel_shapes", "strides", "paddings", "use_bias"]

    # We have to choose asymmetric parameter values here in order for the test
    # to be effective. This is why we don't take the default ones.
    model = module(output_channels=[2, 3, 4],
                   kernel_shapes=[[3, 3], [5, 5], [7, 7]],
                   strides=[[1, 1], [2, 2], [3, 3]],
                   paddings=[snt.SAME, snt.SAME, snt.VALID],
                   use_bias=[True, True, False])

    # We don't pass the parameter on to .transpose, None should be the default
    transpose_model = model.transpose()
    if param_name in expected_reversed:
      self.assertEqual(tuple(reversed(getattr(model, param_name))),
                       getattr(transpose_model, param_name))
    else:
      self.assertEqual(getattr(model, param_name),
                       getattr(transpose_model, param_name))

  @parameterized.parameters(
      *itertools.product(
          [snt.nets.ConvNet2D,
           functools.partial(snt.nets.ConvNet2DTranspose,
                             output_shapes=[[100, 100]])],
          [("kernel_shapes", [[3, 3], [3, 3], [3, 3]]),
           ("strides", [[1, 1], [1, 1], [1, 1]]),
           ("paddings", [snt.SAME, snt.SAME, snt.SAME]),
           ("activation", tf.nn.tanh),
           ("initializers", {}),
           ("partitioners", {}),
           ("regularizers", {}),
           ("use_bias", [True, True, True]),
           ("normalization_ctor", snt.BatchNorm)]))
  def testTransposePassThroughParameter(self, module, param_name_and_value):
    """Tests if .transpose correctly passes through the given parameters.

    Args:
      module: The conv net class.
      param_name_and_value: Tuple consisting of the parameter name and value.
    """
    param_name, param_value = param_name_and_value
    # The given parameter values are all for three-layer networks. Changing
    # the default parameters would therefore break this test. Thus, we choose
    # fixed/independent parameters.
    model = module(output_channels=[2, 3, 4],
                   kernel_shapes=[[3, 3], [5, 5], [7, 7]],
                   strides=[[1, 1], [2, 2], [3, 3]],
                   paddings=[snt.SAME, snt.SAME, snt.VALID],
                   use_bias=[True, True, False])

    transpose_model = model.transpose(**{param_name: param_value})
    if isinstance(param_value, collections.Mapping):
      self.assertDictEqual(param_value, getattr(transpose_model, param_name))
    elif isinstance(param_value, collections.Iterable):
      self.assertCountEqual(param_value, getattr(transpose_model, param_name))
    else:
      self.assertEqual(param_value, getattr(transpose_model, param_name))

  @parameterized.named_parameters(
      ("ConvNet2DNHWC", snt.nets.ConvNet2D, "NHWC"),
      ("ConvNet2DNCHW", snt.nets.ConvNet2D, "NCHW"),
      ("ConvNet2DTransposeNHWC", functools.partial(
          snt.nets.ConvNet2DTranspose, output_shapes=[[100, 100]]), "NHWC"),
      ("ConvNet2DTransposeNCHW", functools.partial(
          snt.nets.ConvNet2DTranspose, output_shapes=[[100, 100]]), "NCHW"),)
  def testDataFormat(self, module, data_format):
    net = module(
        output_channels=self.output_channels,
        kernel_shapes=self.kernel_shapes,
        strides=self.strides,
        paddings=self.paddings,
        data_format=data_format)

    input_height, input_width, input_channels = 100, 100, 3
    batch_size = 10
    final_channel = self.output_channels[-1]
    if data_format == "NHWC":
      input_shape = [batch_size, input_height, input_width, input_channels]
      expected_output_shape = [
          batch_size, input_height, input_width, final_channel
      ]

    else:
      input_shape = [batch_size, input_channels, input_height, input_width]
      expected_output_shape = [
          batch_size, final_channel, input_height, input_width
      ]
    input_to_net = tf.random_normal(dtype=tf.float32, shape=input_shape)

    if tf.executing_eagerly() and data_format == "NCHW":
      if module == snt.nets.ConvNet2D:
        expected_exception = tf.errors.UnimplementedError
      else:
        expected_exception = tf.errors.InvalidArgumentError
      with self.assertRaisesRegexp(expected_exception, "only supports.*NHWC"):
        output = net(input_to_net)

    else:
      output = net(input_to_net)
      self.assertEqual(output.get_shape().as_list(), expected_output_shape)

  @parameterized.parameters(
      # Regular Layer Normalization
      {"conv_ctor": snt.nets.ConvNet2D,
       "norm_ctor": "snt.LayerNorm",
       "norm_kwargs": {"scale": False, "offset": False}},
      {"conv_ctor": functools.partial(
          snt.nets.ConvNet2DTranspose, output_shapes=[[48, 64]]),
       "norm_ctor": snt.LayerNorm,
       "norm_kwargs": {"scale": False, "offset": False}},
      # Instance normalization: sum over spatial dimensions but not channels.
      {"conv_ctor": snt.nets.ConvNet2D,
       "norm_ctor": "LayerNorm",
       "norm_kwargs": {"scale": False, "offset": False, "axis": [1, 2]}},
      {"conv_ctor": functools.partial(
          snt.nets.ConvNet2DTranspose, output_shapes=[[48, 64]]),
       "norm_ctor": snt.LayerNorm,
       "norm_kwargs": {"scale": False, "offset": False, "axis": [1, 2]}},
      )
  def testNormalizations(self, conv_ctor, norm_ctor, norm_kwargs):
    if tf.executing_eagerly():
      self.skipTest("Cannot test normalization correctness in Eager.")
    module = conv_ctor(
        output_channels=[16, 16],
        kernel_shapes=(3,),
        strides=(1,),
        paddings=("SAME",),
        normalization_ctor=norm_ctor,
        normalization_kwargs=norm_kwargs,
        normalize_final=True,
        activate_final=False)  # No final activation, that would un-normalize.
    inputs = tf.random_uniform([16, 48, 64, 3])
    output = module(inputs)
    with tf.train.SingularMonitoredSession() as session:
      output_np = session.run(output)

    # Convert the output into something where all the dimensions that should be
    # jointly normalized are combined to be on axis=1.
    if "axis" in norm_kwargs and norm_kwargs["axis"] == [1, 2]:
      # Check for instance normalization - combine spatial dimensions.
      output_np = np.reshape(output_np, [16, -1, 3])
    else:
      # Check for layer normalization - combine all non-batch dimensions.
      output_np = np.reshape(output_np, [16, -1])
    mean = np.mean(output_np, axis=1)
    std_dev = np.std(output_np, axis=1)
    # High tolerance - summing across big images, this normalization is fairly
    # approximate.
    self.assertAllClose(mean, np.zeros_like(mean), atol=3e-2)
    self.assertAllClose(std_dev, np.ones_like(std_dev), atol=2e-2)

  @parameterized.parameters(
      (snt.nets.ConvNet2D,
       {"use_batch_norm": True, "normalization_ctor": snt.LayerNorm},
       ValueError, "if use_batch_norm is specified"),
      (functools.partial(snt.nets.ConvNet2DTranspose, output_shapes=[[48, 64]]),
       {"use_batch_norm": True, "normalization_ctor": "LayerNorm"},
       ValueError, "if use_batch_norm is specified"),)
  def testNormalizationBadConfig(self, conv_ctor, conv_kwargs,
                                 error_type, error_message):
    """Old and new normalization flags should not be combined."""
    with self.assertRaisesRegexp(error_type, error_message):
      conv_ctor(
          output_channels=[16, 16],
          kernel_shapes=(3,),
          strides=(1,),
          paddings=("SAME",),
          **conv_kwargs)


@contrib_eager.run_all_tests_in_graph_and_eager_modes
class ConvNet2DTest(parameterized.TestCase, tf.test.TestCase):

  def setUp(self):
    super(ConvNet2DTest, self).setUp()
    self.output_channels = [2, 3, 4]
    self.kernel_shapes = [[3, 3]]
    self.strides = [1]
    self.rates = [2]
    self.paddings = [snt.SAME]

  def testConstructor(self):
    net = snt.nets.ConvNet2D(output_channels=self.output_channels,
                             kernel_shapes=self.kernel_shapes,
                             rates=self.rates,
                             strides=self.strides,
                             paddings=self.paddings)
    self.assertLen(net.layers, len(self.output_channels))

    for i, layer in enumerate(net.layers):
      self.assertEqual(layer.output_channels, self.output_channels[i])
      self.assertEqual(layer.stride,
                       (1,) + fill_shape(self.strides[0], 2) + (1,))
      self.assertEqual(layer.kernel_shape, fill_shape(self.kernel_shapes[0], 2))
      self.assertEqual(layer.padding, self.paddings[0])
      self.assertEqual(layer.rate, (self.rates[0], self.rates[0]))
      self.assertEqual(layer.output_channels, net.output_channels[i])
      self.assertEqual(layer.stride,
                       (1,) + fill_shape(net.strides[i], 2) + (1,))
      self.assertEqual(layer.kernel_shape, fill_shape(net.kernel_shapes[i], 2))
      self.assertEqual(layer.padding, net.paddings[i])

  def testTranspose(self):
    with tf.variable_scope("scope1"):
      net = snt.nets.ConvNet2D(output_channels=self.output_channels,
                               kernel_shapes=self.kernel_shapes,
                               strides=self.strides,
                               paddings=self.paddings,
                               name="conv_net_2d")

    err = "Iterable output_channels length must match the number of layers"
    with self.assertRaisesRegexp(ValueError, err):
      net.transpose(output_channels=[42] * 18)

    with tf.variable_scope("scope2"):
      net_transpose = net.transpose()

    self.assertEqual("scope1/conv_net_2d", net.scope_name)
    self.assertEqual("conv_net_2d", net.module_name)
    self.assertEqual("scope2/conv_net_2d_transpose", net_transpose.scope_name)
    self.assertEqual("conv_net_2d_transpose", net_transpose.module_name)

    input_shape = [10, 100, 100, 3]
    input_to_net = tf.random_normal(dtype=tf.float32, shape=input_shape)
    # Tests that trying to connect the trasposed network before connecting the
    # original nets raises an error. The reason is that the output_shapes and
    # output_channels are laziliy evaluated and not yet known.
    with self.assertRaisesRegexp(snt.Error,
                                 "Variables in {} not instantiated yet, "
                                 "__call__ the module first.".format(
                                     net.layers[-1].scope_name)):
      net_transpose(input_to_net)

    net_transpose = net.transpose(name="another_net_transpose")
    net_out = net(input_to_net, is_training=True)
    self.assertEqual(net.input_shape, tuple(input_shape))
    net_transposed_output = net_transpose(net_out)
    self.assertEqual(net_transposed_output.get_shape(),
                     input_to_net.get_shape())
    for i in range(len(net.layers)):
      self.assertEqual(net_transpose.layers[i].output_shape,
                       net.layers[-1 - i].input_shape[1:-1])
      self.assertEqual(net_transpose.layers[i].output_channels,
                       net.layers[-1 - i].input_shape[-1])

  def testCustomGetterTranspose(self):
    """Tests passing a custom getter to the transpose method."""
    conv2d = snt.nets.ConvNet2D(output_channels=self.output_channels,
                                kernel_shapes=self.kernel_shapes,
                                strides=self.strides,
                                paddings=self.paddings)
    input_shape = [10, 100, 100, 3]
    output_of_conv2d = conv2d(tf.zeros(dtype=tf.float32, shape=input_shape))
    # We'll be able to check if the custom_getter was used by checking for
    # gradients.
    conv2d_transpose = conv2d.transpose(
        custom_getter=snt.custom_getters.stop_gradient)
    if tf.executing_eagerly():
      with tf.GradientTape() as tape:
        output_of_transpose = conv2d_transpose(output_of_conv2d)
      conv2d_transpose_vars = conv2d_transpose.get_variables()
      self.assertTrue(len(conv2d_transpose_vars))
      for tensor in tape.gradient(output_of_transpose, conv2d_transpose_vars):
        self.assertIsNone(tensor)

    else:
      output_of_transpose = conv2d_transpose(output_of_conv2d)
      conv2d_transpose_vars = conv2d_transpose.get_variables()
      self.assertTrue(len(conv2d_transpose_vars))
      for tensor in tf.gradients(output_of_transpose, conv2d_transpose_vars):
        self.assertIsNone(tensor)

  def testNoCustomGetterTranspose(self):
    """Tests not passing a custom getter to the transpose method."""
    conv2d = snt.nets.ConvNet2D(output_channels=self.output_channels,
                                kernel_shapes=self.kernel_shapes,
                                strides=self.strides,
                                paddings=self.paddings,
                                custom_getter=snt.custom_getters.stop_gradient)
    input_shape = [10, 100, 100, 3]
    input_to_conv2d = tf.zeros(dtype=tf.float32, shape=input_shape)
    if tf.executing_eagerly():
      with tf.GradientTape() as tape0:
        output_of_conv2d = conv2d(input_to_conv2d)
      # Create a transpose without a custom getter
      conv2d_transpose = conv2d.transpose()
      with tf.GradientTape() as tape1:
        output_of_transpose = conv2d_transpose(output_of_conv2d)
      conv2d_vars = conv2d.get_variables()
      conv2d_grads = tape0.gradient(output_of_conv2d, conv2d_vars)
      conv2d_transpose_vars = conv2d_transpose.get_variables()
      conv2d_transpose_grads = tape1.gradient(output_of_transpose,
                                              conv2d_transpose_vars)
    else:
      output_of_conv2d = conv2d(input_to_conv2d)
      conv2d_vars = conv2d.get_variables()
      conv2d_grads = tf.gradients(output_of_conv2d, conv2d_vars)
      # Create a transpose without a custom getter
      conv2d_transpose = conv2d.transpose()
      output_of_transpose = conv2d_transpose(output_of_conv2d)
      conv2d_transpose_vars = conv2d_transpose.get_variables()
      conv2d_transpose_grads = tf.gradients(output_of_transpose,
                                            conv2d_transpose_vars)

    # Sanity check that the custom getter was indeed used for the conv net.
    self.assertTrue(len(conv2d_vars))
    for tensor in conv2d_grads:
      self.assertIsNone(tensor)
    # Check the transpose did not use the custom getter that was passed to the
    # original conv net.
    self.assertTrue(len(conv2d_transpose_vars))
    for tensor in conv2d_transpose_grads:
      self.assertIsNotNone(tensor)

  def testVariableMap(self):
    """Tests for regressions in variable names."""

    use_bias = True
    use_batch_norm = True
    var_names_w = [
        u"conv_net_2d/conv_2d_0/w:0",
        u"conv_net_2d/conv_2d_1/w:0",
        u"conv_net_2d/conv_2d_2/w:0",
    ]
    var_names_b = [
        u"conv_net_2d/conv_2d_0/b:0",
        u"conv_net_2d/conv_2d_1/b:0",
        u"conv_net_2d/conv_2d_2/b:0",
    ]
    var_names_bn = [
        u"conv_net_2d/batch_norm_0/beta:0",
        u"conv_net_2d/batch_norm_1/beta:0",
    ]

    correct_variable_names = set(var_names_w + var_names_b + var_names_bn)

    module = snt.nets.ConvNet2D(output_channels=self.output_channels,
                                kernel_shapes=self.kernel_shapes,
                                rates=self.rates,
                                strides=self.strides,
                                paddings=self.paddings,
                                use_bias=use_bias,
                                use_batch_norm=use_batch_norm)

    input_shape = [10, 100, 100, 3]
    input_to_net = tf.random_normal(dtype=tf.float32, shape=input_shape)

    _ = module(input_to_net, is_training=True)

    variable_names = [var.name for var in module.get_variables()]

    self.assertEqual(set(variable_names), correct_variable_names)

  def testPartitioners(self):
    if tf.executing_eagerly():
      self.skipTest("Eager does not support partitioned variables.")

    partitioners = {
        "w": tf.variable_axis_size_partitioner(10),
        "b": tf.variable_axis_size_partitioner(8),
    }

    module = snt.nets.ConvNet2D(output_channels=self.output_channels,
                                kernel_shapes=self.kernel_shapes,
                                rates=self.rates,
                                strides=self.strides,
                                paddings=self.paddings,
                                partitioners=partitioners)

    input_shape = [10, 100, 100, 3]
    input_to_net = tf.placeholder(tf.float32, shape=input_shape)

    _ = module(input_to_net)

    for layer in module._layers:
      self.assertEqual(type(layer.w), variables.PartitionedVariable)
      self.assertEqual(type(layer.b), variables.PartitionedVariable)

  def testCustomGetter(self):
    custom_getter = snt.custom_getters.Context(snt.custom_getters.stop_gradient)
    module = snt.nets.ConvNet2D(output_channels=self.output_channels,
                                kernel_shapes=self.kernel_shapes,
                                rates=self.rates,
                                strides=self.strides,
                                paddings=self.paddings,
                                custom_getter=custom_getter)

    input_shape = [10, 100, 100, 3]
    input_to_net = tf.random_normal(dtype=tf.float32, shape=input_shape)

    if tf.executing_eagerly():
      with tf.GradientTape() as tape0:
        out0 = module(input_to_net)
      with tf.GradientTape() as tape1:
        with custom_getter:
          out1 = module(input_to_net)
      all_vars = tf.trainable_variables()
      out0_grads = tape0.gradient(out0, all_vars)
      out1_grads = tape1.gradient(out1, all_vars)

    else:
      out0 = module(input_to_net)
      with custom_getter:
        out1 = module(input_to_net)
      all_vars = tf.trainable_variables()
      out0_grads = tf.gradients(out0, all_vars)
      out1_grads = tf.gradients(out1, all_vars)

    for grad in out0_grads:
      self.assertNotEqual(None, grad)
    self.assertEqual([None] * len(out1_grads), out1_grads)

  def testIncorrectRatesLength(self):
    rates = [1, 2]
    self.assertNotEqual(len(rates), len(self.output_channels))
    with self.assertRaisesRegexp(
        ValueError, "rates must be of length 1 * or"):
      _ = snt.nets.ConvNet2D(output_channels=self.output_channels,
                             kernel_shapes=self.kernel_shapes,
                             rates=rates,
                             strides=self.strides,
                             paddings=self.paddings)

  @parameterized.parameters(
      {"normalization_ctor": None,
       "normalization_kwargs": {}},
      {"normalization_ctor": snt.LayerNorm,
       "normalization_kwargs": {}},
      {"normalization_ctor": snt.LayerNorm,
       "normalization_kwargs": {"axis": [1, 2]}},  # Instance Norm.
      {"normalization_ctor": snt.BatchNorm,
       "normalization_kwargs": {}})
  def testAlwaysProvideIsTraining(self, normalization_ctor,
                                  normalization_kwargs):
    # Test whether we can always provide is_training=True, even when it is
    # not supported by the underlying normalization constructor.
    mod = snt.nets.ConvNet2D(
        output_channels=[32, 32],
        kernel_shapes=(3,),
        strides=(1,),
        paddings=("SAME",),
        normalization_ctor=normalization_ctor,
        normalization_kwargs=normalization_kwargs)
    input_ = tf.random_uniform([16, 48, 48, 3])
    _ = mod(input_, is_training=True)


@contrib_eager.run_all_tests_in_graph_and_eager_modes
class ConvNet2DTransposeTest(parameterized.TestCase, tf.test.TestCase):

  def setUp(self):
    super(ConvNet2DTransposeTest, self).setUp()
    self.output_channels = [2, 3, 4]
    self.output_shapes = [[100, 100]]
    self.kernel_shapes = [[3, 3]]
    self.strides = [1]
    self.paddings = [snt.SAME]

  def testConstructor(self):

    with self.assertRaisesRegexp(ValueError,
                                 "output_shapes must be of length 1 or *"):
      snt.nets.ConvNet2DTranspose(output_channels=self.output_channels,
                                  output_shapes=[],
                                  kernel_shapes=self.kernel_shapes,
                                  strides=self.strides,
                                  paddings=self.paddings)

    with self.assertRaisesRegexp(ValueError,
                                 "output_shapes must be of length 1 or *"):
      snt.nets.ConvNet2DTranspose(output_channels=self.output_channels,
                                  output_shapes=[[1, 2], [1, 2]],
                                  kernel_shapes=self.kernel_shapes,
                                  strides=[],
                                  paddings=self.paddings)

    with self.assertRaisesRegexp(KeyError,
                                 "Invalid initializer keys.*"):
      snt.nets.ConvNet2DTranspose(
          output_channels=self.output_channels,
          output_shapes=self.output_shapes,
          kernel_shapes=self.kernel_shapes,
          strides=self.strides,
          paddings=self.paddings,
          initializers={"not_w": tf.truncated_normal_initializer(stddev=1.0)})

    net = snt.nets.ConvNet2DTranspose(output_channels=self.output_channels,
                                      output_shapes=self.output_shapes,
                                      kernel_shapes=self.kernel_shapes,
                                      strides=self.strides,
                                      paddings=self.paddings)
    self.assertEqual(net.output_shapes,
                     tuple(self.output_shapes) * len(self.output_channels))
    self.assertLen(net.layers, len(self.output_channels))

    for i, layer in enumerate(net.layers):
      self.assertEqual(layer.output_channels, self.output_channels[i])
      self.assertEqual(layer.stride,
                       (1,) + fill_shape(self.strides[0], 2) + (1,))
      self.assertEqual(layer.kernel_shape, fill_shape(self.kernel_shapes[0], 2))
      self.assertEqual(layer.padding, self.paddings[0])
      self.assertEqual(layer.output_channels, net.output_channels[i])
      self.assertEqual(layer.stride,
                       (1,) + fill_shape(net.strides[i], 2) + (1,))
      self.assertEqual(layer.kernel_shape, fill_shape(net.kernel_shapes[i], 2))
      self.assertEqual(layer.padding, net.paddings[i])

    with self.assertRaisesRegexp(TypeError, "output_shapes must be iterable"):
      snt.nets.ConvNet2DTranspose(output_channels=self.output_channels,
                                  output_shapes=False,
                                  kernel_shapes=self.kernel_shapes,
                                  strides=self.strides,
                                  paddings=self.paddings)

  def testTranspose(self):
    net = snt.nets.ConvNet2DTranspose(output_channels=self.output_channels,
                                      output_shapes=self.output_shapes,
                                      kernel_shapes=self.kernel_shapes,
                                      strides=self.strides,
                                      paddings=self.paddings)

    err = "Iterable output_channels length must match the number of layers"
    with self.assertRaisesRegexp(ValueError, err):
      net.transpose(output_channels=[42] * 18)
    net_transpose = net.transpose()
    input_shape = [10, 100, 100, 3]
    input_to_net = tf.random_normal(dtype=tf.float32, shape=input_shape)
    # Tests that trying to connect the trasposed network before connecting the
    # original nets raises an error. The reason is that the output_shapes and
    # output_channels are laziliy evaluated and not yet known.
    with self.assertRaisesRegexp(snt.Error,
                                 "Variables in {} not instantiated yet, "
                                 "__call__ the module first.".format(
                                     net.layers[-1].scope_name)):
      net_transpose(input_to_net)

    net_transpose = net.transpose(name="another_net_transpose")
    net_out = net(input_to_net, is_training=True)
    net_transposed_output = net_transpose(net_out)
    self.assertEqual(net_transposed_output.get_shape(),
                     input_to_net.get_shape())
    for i in range(len(net.layers)):
      self.assertEqual(net_transpose.layers[i].input_shape[1:-1],
                       net.layers[-1 - i].output_shape)
      self.assertEqual(net_transpose.layers[i].output_channels,
                       net.layers[-1 - i].input_shape[-1])

    init = tf.global_variables_initializer()
    self.evaluate(init)
    self.evaluate(net_transposed_output)

  def testPartitioners(self):
    if tf.executing_eagerly():
      self.skipTest("Eager does not support partitioned variables.")

    partitioners = {
        "w": tf.variable_axis_size_partitioner(10),
        "b": tf.variable_axis_size_partitioner(8),
    }

    module = snt.nets.ConvNet2DTranspose(output_channels=self.output_channels,
                                         output_shapes=self.output_shapes,
                                         kernel_shapes=self.kernel_shapes,
                                         strides=self.strides,
                                         paddings=self.paddings,
                                         partitioners=partitioners)

    input_shape = [10, 100, 100, 3]
    input_to_net = tf.placeholder(tf.float32, shape=input_shape)

    _ = module(input_to_net)

    for layer in module._layers:
      self.assertEqual(type(layer.w), variables.PartitionedVariable)
      self.assertEqual(type(layer.b), variables.PartitionedVariable)

  @parameterized.parameters(
      {"normalization_ctor": None,
       "normalization_kwargs": {}},
      {"normalization_ctor": snt.LayerNorm,
       "normalization_kwargs": {}},
      {"normalization_ctor": snt.LayerNorm,
       "normalization_kwargs": {"axis": [1, 2]}},  # Instance Norm.
      {"normalization_ctor": snt.BatchNorm,
       "normalization_kwargs": {}})
  def testAlwaysProvideIsTraining(self, normalization_ctor,
                                  normalization_kwargs):
    # Test whether we can always provide is_training=True, even when it is
    # not supported by the underlying normalization constructor.
    mod = snt.nets.ConvNet2DTranspose(
        output_shapes=self.output_shapes,
        output_channels=self.output_channels,
        kernel_shapes=self.kernel_shapes,
        strides=self.strides,
        paddings=self.paddings,
        normalization_ctor=normalization_ctor,
        normalization_kwargs=normalization_kwargs)
    input_ = tf.random_uniform([16, 100, 100, 3])
    _ = mod(input_, is_training=True)

  def testCustomGetter(self):
    custom_getter = snt.custom_getters.Context(snt.custom_getters.stop_gradient)
    module = snt.nets.ConvNet2DTranspose(
        output_shapes=self.output_shapes,
        output_channels=self.output_channels,
        kernel_shapes=self.kernel_shapes,
        strides=self.strides,
        paddings=self.paddings,
        custom_getter=custom_getter)

    input_shape = [10, 100, 100, 3]
    input_to_net = tf.random_normal(dtype=tf.float32, shape=input_shape)

    if tf.executing_eagerly():
      with tf.GradientTape() as tape0:
        out0 = module(input_to_net)
      with tf.GradientTape() as tape1:
        with custom_getter:
          out1 = module(input_to_net)
      all_vars = tf.trainable_variables()
      out0_grads = tape0.gradient(out0, all_vars)
      out1_grads = tape1.gradient(out1, all_vars)

    else:
      out0 = module(input_to_net)
      with custom_getter:
        out1 = module(input_to_net)
      all_vars = tf.trainable_variables()
      out0_grads = tf.gradients(out0, all_vars)
      out1_grads = tf.gradients(out1, all_vars)

    for grad in out0_grads:
      self.assertIsNotNone(grad)
    self.assertEqual([None] * len(out1_grads), out1_grads)

  def testCustomGetterTranspose(self):
    """Tests passing a custom getter to the transpose method."""
    conv2d_t = snt.nets.ConvNet2DTranspose(
        output_shapes=self.output_shapes,
        output_channels=self.output_channels,
        kernel_shapes=self.kernel_shapes,
        strides=self.strides,
        paddings=self.paddings)
    input_shape = [10, 100, 100, 3]
    output_of_conv2d_t = conv2d_t(tf.zeros(dtype=tf.float32, shape=input_shape))
    # We'll be able to check if the custom_getter was used by checking for
    # gradients.
    conv2d = conv2d_t.transpose(custom_getter=snt.custom_getters.stop_gradient)
    if tf.executing_eagerly():
      with tf.GradientTape() as tape:
        output_of_conv = conv2d(output_of_conv2d_t)
      conv2d_vars = conv2d.get_variables()
      self.assertTrue(len(conv2d_vars))
      for tensor in tape.gradient(output_of_conv, conv2d_vars):
        self.assertIsNone(tensor)

    else:
      output_of_conv = conv2d(output_of_conv2d_t)
      conv2d_vars = conv2d.get_variables()
      self.assertTrue(len(conv2d_vars))
      for tensor in tf.gradients(output_of_conv, conv2d_vars):
        self.assertIsNone(tensor)

  def testNoCustomGetterTranspose(self):
    """Tests not passing a custom getter to the transpose method."""
    conv2d_t = snt.nets.ConvNet2DTranspose(
        output_shapes=self.output_shapes,
        output_channels=self.output_channels,
        kernel_shapes=self.kernel_shapes,
        strides=self.strides,
        paddings=self.paddings,
        custom_getter=snt.custom_getters.stop_gradient)
    input_shape = [10, 100, 100, 3]
    input_to_conv2d_t = tf.zeros(dtype=tf.float32, shape=input_shape)
    if tf.executing_eagerly():
      with tf.GradientTape() as tape0:
        output_of_conv2d_t = conv2d_t(input_to_conv2d_t)
      # Create a transpose without a custom getter
      conv2d = conv2d_t.transpose()
      with tf.GradientTape() as tape1:
        output_of_conv = conv2d(output_of_conv2d_t)
      conv2d_t_vars = conv2d_t.get_variables()
      conv2d_t_grads = tape0.gradient(output_of_conv2d_t, conv2d_t_vars)
      conv2d_vars = conv2d.get_variables()
      conv2d_grads = tape1.gradient(output_of_conv, conv2d_vars)
    else:
      output_of_conv2d_t = conv2d_t(input_to_conv2d_t)
      conv2d_t_vars = conv2d_t.get_variables()
      conv2d_t_grads = tf.gradients(output_of_conv2d_t, conv2d_t_vars)
      # Create a transpose without a custom getter
      conv2d = conv2d_t.transpose()
      output_of_conv = conv2d(output_of_conv2d_t)
      conv2d_vars = conv2d.get_variables()
      conv2d_grads = tf.gradients(output_of_conv, conv2d_vars)

    # Sanity check that the custom getter was indeed used for the conv net.
    self.assertTrue(len(conv2d_t_vars))
    for tensor in conv2d_t_grads:
      self.assertIsNone(tensor)
    # Check the transpose did not use the custom getter that was passed to the
    # original conv net.
    self.assertTrue(len(conv2d_vars))
    for tensor in conv2d_grads:
      self.assertIsNotNone(tensor)


@contrib_eager.run_all_tests_in_graph_and_eager_modes
class DefunTest(parameterized.TestCase, tf.test.TestCase):

  @parameterized.named_parameters(
      ("ConvNet2D", snt.nets.ConvNet2D),
      ("ConvNet2DTranspose",
       functools.partial(snt.nets.ConvNet2DTranspose,
                         output_shapes=[[100, 100]])))
  def testDefun(self, module):
    model = module(output_channels=[2, 3, 4],
                   kernel_shapes=[[3, 3]],
                   strides=[1],
                   paddings=[snt.SAME])

    model = contrib_eager.defun(model)
    input_to_net = tf.random_normal([1, 100, 100, 3])
    output = model(input_to_net)
    self.assertListEqual(output.shape.as_list(), [1, 100, 100, 4])

if __name__ == "__main__":
  tf.test.main()
