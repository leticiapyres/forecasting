import tensorflow as tf
from tensorflow.python.util import nest
import tensorflow.contrib.layers as layers
import tensorflow.contrib.rnn as rnn
import tensorflow.contrib.cudnn_rnn as cudnn_rnn
RNN = cudnn_rnn.CudnnGRU
GRAD_CLIP_THRESHOLD = 10


# input pipe utils
def cut(ts_value_train_slice, feature_train_slice,
        feature_test_slice, train_window, predict_window,
        cut_mode='train', back_offset=0):
    """
    cut each element of the dataset into x and y for supervised learning.

    :param ts_value_train_slice: shape of (#train_ts_length,)
    :param feature_train_slice: shape of (#train_ts_length, #features)
    :param feature_test_slice: shape of (#test_ts_length, #features)
    :param cut_mode: 'train', 'eval', 'predict'
    :param back_offset: how many data points at end of time series
            cannot be used for training.
            set back_offset = predict_window for training
            during hyper parameter tuning.

    :return:
    """
    ts_length = tf.shape(ts_value_train_slice)[0]
    if cut_mode in ['train', 'eval']:
        if cut_mode == 'train':
            min_start_idx = 0
            max_start_idx = (ts_length - back_offset) - \
                            (train_window + predict_window) + 1
            train_start = tf.random_uniform((), min_start_idx, max_start_idx,
                                            dtype=tf.int32)
        elif cut_mode == 'eval':
            train_start = ts_length - (train_window + predict_window)

        train_end = train_start + train_window
        test_start = train_end
        test_end = test_start + predict_window

        true_x = ts_value_train_slice[train_start: train_end]
        true_y = ts_value_train_slice[test_start: test_end]
        feature_x = feature_train_slice[train_start: train_end]
        feature_y = feature_train_slice[test_start: test_end]

    else:
        train_start = ts_length - train_window
        train_end = train_start + train_window

        true_x = ts_value_train_slice[train_start: train_end]
        true_y = None
        feature_x = feature_train_slice[train_start: train_end]
        feature_y = feature_test_slice

    return true_x, true_y, feature_x, feature_y


def normalize_target(true_x, true_y, feature_x, feature_y):
    """
    normalize the target variable.
    """
    masked_true_x = tf.boolean_mask(true_x, tf.logical_not(tf.is_nan(true_x)))

    norm_mean = tf.reduce_mean(masked_true_x)
    norm_std = tf.sqrt(tf.reduce_mean(tf.squared_difference(masked_true_x, norm_mean)))
    norm_x = (true_x - norm_mean) / norm_std
    # question: the std returned is actually 1 / std?
    return true_x, true_y, feature_x, feature_y, norm_x, norm_mean, norm_std


# model utils
def make_encoder(time_inputs, is_train, hparams):
    """
    Builds encoder, using CUDA RNN
    """

    def build_rnn():
        return RNN(num_layers=hparams.encoder_rnn_layers, num_units=hparams.rnn_depth,
                   kernel_initializer=tf.initializers.random_uniform(minval=-0.05, maxval=0.05),
                   direction='unidirectional',
                   dropout=hparams.encoder_dropout if is_train else 0)

    cuda_model = build_rnn()

    # [batch, time, features] -> [time, batch, features]
    time_first = tf.transpose(time_inputs, [1, 0, 2])
    rnn_time_input = time_first
    # rnn_out: (time, batch, rnn_depth)
    # rnn_state: (num_layers, batch, rnn_depth)
    rnn_out, (rnn_state,) = cuda_model(inputs=rnn_time_input)
    return rnn_out, rnn_state


def convert_cudnn_state_v2(h_state, hparams, dropout=1.0):
    """
    Converts RNN state tensor from cuDNN representation to TF RNNCell compatible representation.
    :param h_state: tensor [num_layers, batch_size, depth]
    :param c_state: LSTM additional state, should be same shape as h_state
    :return: TF cell representation matching RNNCell.state_size structure for compatible cell
    """

    def squeeze(seq):
        return tuple(seq) if len(seq) > 1 else seq[0]

    def wrap_dropout(structure):
        if dropout < 1.0:
            return nest.map_structure(lambda x: tf.nn.dropout(x, keep_prob=dropout), structure)
        else:
            return structure

    # Cases:
    # decoder_layer = encoder_layers, straight mapping
    # encoder_layers > decoder_layers: get outputs of upper encoder layers
    # encoder_layers < decoder_layers: feed encoder outputs to lower decoder layers, feed zeros to top layers
    h_layers = tf.unstack(h_state)
    if hparams.encoder_rnn_layers >= hparams.decoder_rnn_layers:
        return squeeze(wrap_dropout(h_layers[hparams.encoder_rnn_layers - hparams.decoder_rnn_layers:]))
    else:
        lower_inputs = wrap_dropout(h_layers)
        upper_inputs = [tf.zeros_like(h_layers[0]) for _ in
                        range(hparams.decoder_rnn_layers - hparams.encoder_rnn_layers)]
        return squeeze(lower_inputs + upper_inputs)


def default_init():
    # replica of tf.glorot_uniform_initializer(seed=seed)
    return layers.variance_scaling_initializer(factor=1.0,
                                               mode="FAN_AVG",
                                               uniform=True)


def decoder(encoder_state, prediction_inputs, previous_y, hparams, is_train, predict_window):
    """
    :param encoder_state: shape [batch_size, encoder_rnn_depth]
    :param prediction_inputs: features for prediction days, tensor[batch_size, time, input_depth]
    :param previous_y: Last day pageviews, shape [batch_size]
    """

    def build_cell(idx):
        with tf.variable_scope('decoder_cell', initializer=default_init()):
            cell = rnn.GRUBlockCell(hparams.rnn_depth)
            has_dropout = hparams.decoder_input_dropout[idx] < 1 \
                          or hparams.decoder_state_dropout[idx] < 1 or hparams.decoder_output_dropout[idx] < 1

            if is_train and has_dropout:
                input_size = prediction_inputs.shape[-1].value + 1 if idx == 0 else hparams.rnn_depth
                cell = rnn.DropoutWrapper(cell, dtype=tf.float32, input_size=input_size,
                                          variational_recurrent=hparams.decoder_variational_dropout[idx],
                                          input_keep_prob=hparams.decoder_input_dropout[idx],
                                          output_keep_prob=hparams.decoder_output_dropout[idx],
                                          state_keep_prob=hparams.decoder_state_dropout[idx])
            return cell

    if hparams.decoder_rnn_layers > 1:
        cells = [build_cell(idx) for idx in range(hparams.decoder_rnn_layers)]
        cell = rnn.MultiRNNCell(cells)
    else:
        cell = build_cell(0)

    nest.assert_same_structure(encoder_state, cell.state_size)

    # [batch_size, time, input_depth] -> [time, batch_size, input_depth]
    inputs_by_time = tf.transpose(prediction_inputs, [1, 0, 2])

    # Stop condition for decoding loop
    def cond_fn(time, prev_output, prev_state, array_targets: tf.TensorArray, array_outputs: tf.TensorArray):
        return time < predict_window

    # FC projecting layer to get single predicted value from RNN output
    def project_output(tensor):
        return tf.layers.dense(tensor, 1, name='decoder_output_proj', kernel_initializer=default_init())

    def loop_fn(time, prev_output, prev_state, array_targets: tf.TensorArray, array_outputs: tf.TensorArray):
        """
        Main decoder loop
        :param time: Day number
        :param prev_output: Output(prediction) from previous step
        :param prev_state: RNN state tensor from previous step
        :param array_targets: Predictions, each step will append new value to this array
        :param array_outputs: Raw RNN outputs (for regularization losses)
        :return:
        """
        # RNN inputs for current step
        features = inputs_by_time[time]

        # [batch, predict_window, readout_depth * n_heads] -> [batch, readout_depth * n_heads]
        # Append previous predicted value to input features
        next_input = tf.concat([prev_output, features], axis=1)


        # Run RNN cell
        output, state = cell(next_input, prev_state)
        # Make prediction from RNN outputs
        projected_output = project_output(output)
        # Append step results to the buffer arrays
        array_targets = array_targets.write(time, projected_output)
        # Increment time and return
        return time + 1, projected_output, state, array_targets, array_outputs

    # Initial values for loop
    loop_init = [tf.constant(0, dtype=tf.int32),
                 tf.expand_dims(previous_y, -1),
                 encoder_state,
                 tf.TensorArray(dtype=tf.float32, size=predict_window),
                 tf.constant(0)]
    # Run the loop
    _, _, _, targets_ta, outputs_ta = tf.while_loop(cond_fn, loop_fn, loop_init)

    # Get final tensors from buffer arrays
    targets = targets_ta.stack()
    # [time, batch_size, 1] -> [time, batch_size]
    targets = tf.squeeze(targets, axis=-1)
    raw_outputs = None
    return targets, raw_outputs


def decode_predictions(decoder_readout, norm_mean, norm_std):
    """
    Converts normalized prediction values to log1p(pageviews), e.g. reverts normalization
    :param decoder_readout: Decoder output, shape [n_days, batch]
    :param inp: Input tensors
    :return:
    """
    # [n_days, batch] -> [batch, n_days]
    batch_readout = tf.transpose(decoder_readout)
    batch_std = tf.expand_dims(norm_std, -1)
    batch_mean = tf.expand_dims(norm_mean, -1)
    return batch_readout * batch_std + batch_mean


def calc_mape_rounded(true, predicted, weights):
    """
    Calculates MAPE on rounded submission values. Should be close to official MAPE in competition
    :param true:
    :param predicted:
    :param weights: Weights mask to exclude some values
    :return:
    """
    n_valid = tf.reduce_sum(weights)
    true_o = tf.round(tf.expm1(true))
    pred_o = tf.maximum(tf.round(tf.expm1(predicted)), 0.0)
    raw_mape = tf.abs(pred_o - true_o) / tf.abs(true_o)
    return tf.reduce_sum(raw_mape * weights) / n_valid


def mape_loss(true, predicted, weights):
    """
    Differentiable MAPE loss
    :param true: Truth values
    :param predicted: Predicted values
    :param weights: Weights mask to exclude some values
    :return:
    """
    epsilon = 0.1  # Smoothing factor, helps SMAPE to be well-behaved near zero
    true_o = tf.expm1(true)
    pred_o = tf.expm1(predicted)
    summ = tf.maximum(tf.abs(true_o) + epsilon, 0.5 + epsilon)
    mape = tf.abs(pred_o - true_o) / summ
    return tf.losses.compute_weighted_loss(mape, weights, loss_collection=None)


def calc_loss(predictions, true_y, additional_mask=None):
    """
    Calculates losses, ignoring NaN true values (assigning zero loss to them)
    :param predictions: Predicted values
    :param true_y: True values
    :param additional_mask:
    :return: MAE loss, differentiable MAPE loss, competition MAPE loss
    """
    # Take into account NaN's in true values
    mask = tf.logical_not(tf.is_nan(true_y))
    # Fill NaNs by zeros (can use any value)
    true_y = tf.where(mask, true_y, tf.zeros_like(true_y))
    # Assign zero weight to NaNs
    weights = tf.to_float(mask)
    if additional_mask is not None:
        weights = weights * tf.expand_dims(additional_mask, axis=0)

    mae_loss = tf.losses.absolute_difference(labels=true_y, predictions=predictions, weights=weights)
    return mae_loss, mape_loss(true_y, predictions, weights), \
           calc_mape_rounded(true_y, predictions, weights), tf.size(true_y)


def make_train_op(loss, ema_decay=None, prefix=None):
    optimizer = tf.train.AdamOptimizer()
    glob_step = tf.train.get_global_step()

    # Add regularization losses
    reg_losses = tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES)
    total_loss = loss + reg_losses if reg_losses else loss

    # Clip gradients
    grads_and_vars = optimizer.compute_gradients(total_loss)
    gradients, variables = zip(*grads_and_vars)
    clipped_gradients, glob_norm = tf.clip_by_global_norm(gradients, GRAD_CLIP_THRESHOLD)
    sgd_op, glob_norm = optimizer.apply_gradients(zip(clipped_gradients, variables)), glob_norm

    # Apply SGD averaging
    if ema_decay:
        ema = tf.train.ExponentialMovingAverage(decay=ema_decay, num_updates=glob_step)
        if prefix:
            # Some magic to handle multiple models trained in single graph
            ema_vars = [var for var in variables if var.name.startswith(prefix)]
        else:
            ema_vars = variables
        update_ema = ema.apply(ema_vars)
        with tf.control_dependencies([sgd_op]):
            training_op = tf.group(update_ema)
    else:
        training_op = sgd_op
        ema = None
    return training_op, glob_norm, ema
