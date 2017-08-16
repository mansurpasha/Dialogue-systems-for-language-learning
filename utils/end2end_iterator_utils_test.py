"""
A dialogue system meant to be used for language learning.

This is based on Google Neural Machine Tranlation model
https://github.com/tensorflow/nmt
which is based on Thang Luong's thesis on
Neural Machine Translation: https://github.com/lmthang/thesis

And on the paper Building End-To-End Dialogue Systems
Using Generative Hierarchical Neural Network Models:
https://arxiv.org/pdf/1507.04808.pdf

Created by Tudor Paraschivescu for the Cambridge UROP project
"Dialogue systems for language learning"

Tests for end2end_iterator_utils.py
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
from tensorflow.python.ops import lookup_ops

from utils import end2end_iterator_utils


class IteratorUtilsTest(tf.test.TestCase):
    def testGetIterator(self):
        dataset = tf.contrib.data.Dataset.from_tensor_slices(
            tf.constant(["a b b a eou c a b  eou a c c c eou a b c a",
                         "a b eou f a eou b eou c eou a",
                         "a c eou b f a f eou c a a a",
                         "a eou b "])
        )
        vocab_table = lookup_ops.index_table_from_tensor(
            tf.constant(["a", "b", "c", "sos", "eos", "eou"])
        )

        batch_size = 2
        src_reverse = False
        sos = 'sos'
        eos = "eos"
        eou = "eou"
        random_seed = 53
        num_buckets = 2
        src_max_len = 3
        tgt_max_len = 2
        dialogue_max_len = 4
        skip_count = None

        iterator = end2end_iterator_utils.get_iterator(dataset, vocab_table, batch_size, sos, eos, eou, src_reverse,
                                                       random_seed, num_buckets, dialogue_max_len, src_max_len,
                                                       tgt_max_len, skip_count=skip_count)
        source = iterator.source
        target_in = iterator.target_input
        target_out = iterator.target_output
        source_len = iterator.source_sequence_length
        target_len = iterator.target_sequence_length
        dialogue_len = iterator.dialogue_length

        self.assertEqual([None, None, None], source.shape.as_list())
        self.assertEqual([None, None, None], target_in.shape.as_list())
        self.assertEqual([None, None, None], target_out.shape.as_list())
        self.assertEqual([None], source_len.shape.as_list())
        self.assertEqual([None], target_len.shape.as_list())
        self.assertEqual([None], dialogue_len.shape.as_list())

        with self.test_session() as sess:
            sess.run(tf.tables_initializer())
            sess.run(iterator.initializer)

            (src_eval, tgt_in, tgt_out, src_seq_len, tgt_seq_len, diag_len) = (sess.run((source, target_in, target_out,
                                                                                         source_len, target_len,
                                                                                         dialogue_len)))
            self.assertAllEqual(
                [[[0, 1, 1],  # a b b, cut off because of src_max_len
                  [0, 2, 2]],  # a c c
                 # These two are batched together because of bucketing
                 [[0, 2, 4],  # a c pad=eos, because we use eos for padding. I will differentiate them in comments
                  [2, 0, 0]]],  # c a a
                src_eval
            )
            self.assertAllEqual(
                [[[3, 2, 0],  # sos c a. Truncated because of tgt_max_len
                  [3, 0, 1]],  # sos a b

                 [[3, 1, -1],  # sos b f='unknown'
                  [4, 4, 4]]],  # pad pad pad, because there's not response.
                tgt_in
            )
            self.assertAllEqual(
                [[[2, 0, 4],  # c a eos
                  [0, 1, 4]],  # a b eos

                 [[1, -1, 4],  # b f='unknown' eos
                  [4, 4, 4]]],  # pad pad pad
                tgt_out
            )
            self.assertAllEqual(
                [3, 3],  # Both have been truncated to 3
                src_seq_len
            )
            self.assertAllEqual(
                [3, 3],  # we include padding
                tgt_seq_len
            )
            self.assertAllEqual(
                [2, 1],  # because for the second one we have only one exchange
                diag_len
            )

            # Get next batch
            (src_eval, tgt_in, tgt_out, src_seq_len, tgt_seq_len, diag_len) = (sess.run((source, target_in, target_out,
                                                                                         source_len, target_len,
                                                                                         dialogue_len)))

            self.assertAllEqual(
                [[[0, 4],  # a pad
                  [4, 4]],  # pad pad
                 # In this order because when carrying on we first look at the next elem, 4, and then batch em.
                 [[0, 1],  # a b
                  [1, 4]]],  # b pad
                # Note that it has been cut of short because of dialogue_max_len
                src_eval
            )
            self.assertAllEqual(
                [[[3, 1, 4],  # sos b
                  [4, 4, 4]],  # pad pad

                 [[3, -1, 0],  # sos f='unknown' a
                  [3, 2, 4]]],  # sos c pad
                tgt_in
            )
            self.assertAllEqual(
                [[[1, 4, 4],  # b eos
                  [4, 4, 4]],  # pad pad

                 [[-1, 0, 4],  # f='unknown' a eos
                  [2, 4, 4]]],  # c pad eos
                tgt_out
            )
            self.assertAllEqual(
                [1, 2],  # Remember that they are switched
                src_seq_len
            )
            self.assertAllEqual(
                [2, 3],  # Because of padding
                tgt_seq_len
            )
            self.assertAllEqual(
                [1, 2],
                diag_len
            )

    def testGetInferIterator(self):
        dataset = tf.contrib.data.Dataset.from_tensor_slices(
            tf.constant(["a b b a eou c ", "a c eou f", "a eou b eou c", "d"])
        )
        vocab_table = lookup_ops.index_table_from_tensor(
            tf.constant(["a", "b", "c", "eos", "eou"])
        )

        batch_size = 2
        src_reverse = False
        eos = "eos"
        eou = "eou"
        utt_max_len = 3
        dialogue_max_len = 2

        iterator = end2end_iterator_utils.get_infer_iterator(dataset, vocab_table,
                                                             batch_size, src_reverse, eos, eou,
                                                             utt_max_len, dialogue_max_len)

        source = iterator.source
        seq_len = iterator.source_sequence_length
        diag_len = iterator.dialogue_length
        self.assertEqual([None, None, None], source.shape.as_list())
        self.assertEqual([None], seq_len.shape.as_list())
        self.assertEqual([None], diag_len.shape.as_list())
        with self.test_session() as sess:
            sess.run(tf.tables_initializer())
            sess.run(iterator.initializer)

            (src_eval, seq_len_eval, diag_len_eval) = sess.run((source, seq_len, diag_len))

            self.assertAllEqual(
                [[[0, 1, 1],  # a b b, cut off because of utt_max_len
                  [2, 3, 3]],  # c pad pad, where pad is the eos in this case

                 [[0, 2, 3],  # a c pad, because it pads it to the previous one's length
                  [-1, 3, 3]]],  # f='unknown', pad pad
                src_eval
            )
            self.assertAllEqual(
                [3, 2],  # a b b (because of utt_max_len) and a c
                seq_len_eval
            )
            self.assertAllEqual(
                [2, 2],
                diag_len_eval
            )

            (src_eval, seq_len_eval, diag_len_eval) = sess.run((source, seq_len, diag_len))

            self.assertAllEqual(
                [[[0],  # a
                  [1]],  # b

                 [[-1],  # d=unknown
                  [3]]],  # pad
                src_eval
            )
            self.assertAllEqual([1, 1], seq_len_eval)
            self.assertAllEqual([2, 1], diag_len_eval)


if __name__ == '__main__':
    tf.test.main()