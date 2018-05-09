# -*- coding: utf-8 -*-
import tensorflow as tf
import numpy as np

class Char_CNN():
    def __init__(self, config, conv_layers, fc_layers):
        self.config = config
        self.embedding = config.emb
        self.input_len = config.strmaxlen
        self.output_dim = config.output
        self.char_size = config.charsize
        self.conv_layers = conv_layers
        self.fc_layers = fc_layers

        with tf.name_scope("Input-Layer"):
            # Input
            self.x1 = tf.placeholder(tf.int64, shape=[None, self.input_len], name="input_x")
            self.y_ = tf.placeholder(tf.int64, shape=[None], name="output_x")
            keep_prob = tf.placeholder(tf.float32, name="dropout_keep_prob")
            # Embedding == 0 : One-hot, != 0, Embedding
            if self.embedding != 0:
                init = tf.contrib.layers.xavier_initializer(uniform=False)
                embedding_matrix = tf.get_variable('embedding_matrix', [self.char_size, self.embedding], initializer=init)

        # EMBEDDING LAYERS
        with tf.name_scope("Embedding-Layer"):
            # one hot encoding of zero vector, 0, 1, 2, ... , char_size - 1
            one_hot = tf.concat(
                [
                    tf.zeros([1, self.char_size]),
                    tf.one_hot(list(range(self.char_size)), self.char_size, 1.0, 0.0)
                ],
                0
            )
            # CNN (tf.conv2d) : input = [batch, in_height, in_width, in_channels]
            # NLP embedding only has 1 channels
            # shape = (Batch, input_len, Embedding, 1)
            if self.embedding == 0:
                cnn_x = tf.nn.embedding_lookup(one_hot, self.x1)
            else:
                cnn_x = tf.nn.embedding_lookup(embedding_matrix, self.x1)
            cnn_x = tf.expand_dims(cnn_x, -1)

        # CONVOLUTION LAYERS
        for i, conv_info in enumerate(self.conv_layers):

            # conv_info = [# of feature, kernel height, pool height]
            with tf.name_scope("Conv-Layer" + str(i)):
                filter_width = cnn_x.get_shape()[2].value
                filter_shape = [conv_info[1], filter_width, 1, conv_info[0]]

                W = tf.Variable(tf.random_normal(filter_shape,  mean=0.0, stddev=0.05), dtype=tf.float32,
                                name='Conv_W')  # large = 0.02 , small = 0.05
                b = tf.Variable(tf.random_normal(shape=[conv_info[0]],  mean=0.0, stddev=0.05), dtype=tf.float32,
                                name='Conv_b')

                conv = tf.nn.conv2d(cnn_x, W, [1, 1, 1, 1], "VALID", name="conv")
                cnn_x = tf.nn.bias_add(conv, b)

            with tf.name_scope("Non-Linear"):
                cnn_x = tf.nn.relu(cnn_x)
            if conv_info[-1] != -1:
                with tf.name_scope("Max-Polling"):
                    pool_shape = [1, conv_info[-1], 1, 1]
                    pool = tf.nn.max_pool(cnn_x, ksize=pool_shape, strides=pool_shape, padding="VALID")
                    cnn_x = tf.transpose(pool, [0, 1, 3, 2])
            else:
                cnn_x = tf.transpose(cnn_x, [0, 1, 3, 2])
        cnn_output = tf.squeeze(cnn_x, axis=3)

        out_shape = cnn_output.get_shape()
        d = out_shape[1].value * out_shape[2].value
        fc_input = tf.reshape(cnn_output, [-1, d])

        for i, fc_dim in enumerate(self.fc_layers):
            with tf.name_scope("FC-Layer-" + str(i)):
                W = tf.Variable(tf.random_normal([d, fc_dim], mean=0.0, stddev=0.05), dtype=tf.float32,
                                name="Output_W" + str(i))
                b = tf.Variable(tf.random_normal([fc_dim], mean=0.0, stddev=0.05), dtype=tf.float32,
                                name="Output_b" + str(i))
                fc_input = tf.nn.xw_plus_b(fc_input, W, b, name="FC"+str(i))
                fc_input = tf.nn.dropout(tf.nn.relu(fc_input), 0.5)
                d = fc_dim

        fc_output = fc_input

        with tf.name_scope("Output-Layer"):
            W = tf.Variable(tf.random_normal([d, self.output_dim], mean=0.0, stddev=0.05), dtype=tf.float32,
                            name="Output_W")
            b = tf.Variable(tf.random_normal([self.output_dim], mean=0.0, stddev=0.05), dtype=tf.float32,
                            name="Output_b")

            output = tf.nn.xw_plus_b(fc_output, W, b, name="output_prob")

            self.prediction = tf.argmax(output, axis=1)


        with tf.name_scope("Loss"):
            one_hot_label = tf.one_hot(self.y_, depth=self.output_dim)
            cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(logits=output, labels=tf.stop_gradient(one_hot_label))
            self.loss = tf.reduce_mean(cross_entropy)

        with tf.name_scope("Accuracy"):
            correct_predictions = tf.equal(self.prediction, self.y_)
            self.accuracy = tf.reduce_mean(tf.cast(correct_predictions, "float"), name="accuracy")

        global_step = tf.Variable(0, trainable=False)
        decayed_lr = tf.train.exponential_decay(config.lr, global_step, 3 * config.num_batch, 0.5, True)
        # optimizer = tf.train.AdamOptimizer(learning_rate=config.lr)
        optimizer = tf.train.MomentumOptimizer(learning_rate=decayed_lr, momentum=0.9)
        self.train_step = optimizer.minimize(self.loss, global_step=global_step)

    def __str__(self):
        name = "Char_CNN"
        embeddings = "Embedding Size : " + str(self.embedding)
        filter_num = "Number of Filters : " + str(self.config.filter_num)
        layers = "Conv Layers : " + str(self.conv_layers)
        fc_layers = "FC Layers : " + str(self.fc_layers)

        return '\n'.join([name, embeddings, filter_num, layers, fc_layers])