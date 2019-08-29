#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import argparse
import numpy as np
import wave
import csv
import os
#import tensorflow as tf
import sys
import resource

from six.moves import zip, range
from multiprocessing import JoinableQueue, Process, cpu_count, Manager
from deepspeech import Model

from util.evaluate_tools import calculate_report

r'''
This module should be self-contained:
  - build libdeepspeech.so with TFLite:
    - bazel build [...] --define=runtime=tflite [...] //native_client:libdeepspeech.so
  - make -C native_client/python/ TFDIR=... bindings
  - setup a virtualenv
  - pip install native_client/python/dist/deepspeech*.whl
  - pip install -r requirements_eval_tflite.txt
Then run with a TF Lite model, alphabet, LM/trie and a CSV test file
'''

BEAM_WIDTH = 500
LM_ALPHA = 0.75
LM_BETA = 1.85
N_FEATURES = 26
N_CONTEXT = 9

def memory_limit(rate):
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (get_memory() * 1024 * rate, hard))

def get_memory():
    with open('/proc/meminfo', 'r') as mem:
        free_memory = 0
        for i in mem:
            sline = i.split()
            if str(sline[0]) in ('MemFree:', 'Buffers:', 'Cached:'):
                free_memory += int(sline[1])
    return free_memory

def tflite_worker(model, alphabet, lm, trie, queue_in, queue_out, gpu_mask):
    os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_mask)
    #os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    ds = Model(model, N_FEATURES, N_CONTEXT, alphabet, BEAM_WIDTH)
    ds.enableDecoderWithLM(alphabet, lm, trie, LM_ALPHA, LM_BETA)

    while True:
        msg = queue_in.get()

        filename = msg['filename']
        wavname = os.path.splitext(os.path.basename(filename))[0]
        fin = wave.open(filename, 'rb')
        fs = fin.getframerate()
        audio = np.frombuffer(fin.readframes(fin.getnframes()), np.int16)
        fin.close()

        decoded = ds.stt(audio, fs)

        queue_out.put({'wav': wavname, 'prediction': decoded})
        print(queue_out.qsize(), end='\r') # Update the current progress
        queue_in.task_done()

def main():
    parser = argparse.ArgumentParser(description='Computing TFLite accuracy')
    parser.add_argument('--model', required=True,
                        help='Path to the model (protocol buffer binary file)')
    parser.add_argument('--alphabet', required=True,
                        help='Path to the configuration file specifying the alphabet used by the network')
    parser.add_argument('--lm', required=True,
                        help='Path to the language model binary file')
    parser.add_argument('--trie', required=True,
                        help='Path to the language model trie file created with native_client/generate_trie')
    parser.add_argument('--csv', required=True,
                        help='Path to the csv source file')
    parser.add_argument('--proc', required=False, default=cpu_count(), type=int,
                        help='Number of processes to spawn, defaulting to number of CPUs')
    parser.add_argument('--dump', required=False, action='store_true', default=False,
                        help='Dump the results as text file, with one line for each wav: "wav transcription"')
    args = parser.parse_args()
    
    memory_limit(0.5)

    manager = Manager()
    work_todo = JoinableQueue()   # this is where we are going to store input data
    work_done = manager.Queue()  # this where we are gonna push them out

    #tf.get_default_graph().as_default()
    #tf.reset_default_graph()
    #tfconfig = tf.ConfigProto()
    #tfconfig.gpu_options.per_process_gpu_memory_fraction = 0.1
    #tfconfig.gpu_options.allow_growth = True
    #tfconfig.allow_soft_placement=True

    processes = []
    for i in range(args.proc):
        worker_process = Process(target=tflite_worker, args=(args.model, args.alphabet, args.lm, args.trie, work_todo, work_done, i), daemon=True, name='tflite_process_{}'.format(i))
        worker_process.start()        # Launch reader() as a separate python process
        processes.append(worker_process)

    print([x.name for x in processes])

    wavlist = []
    predictions = []

    with open(args.csv, 'r') as csvfile:
        csvreader = csv.DictReader(csvfile)
        count = 0
        for row in csvreader:
            count += 1
            work_todo.put({'filename': row['wav_filename']})
    print('Totally %d wav entries found in csv\n' % count)
    work_todo.join()
    num_work = work_done.qsize()
    print('\nTotally %d wav file transcripted' % num_work)

    while not work_done.empty():
        msg = work_done.get()
        predictions.append(msg['prediction'])
        wavlist.append(msg['wav'])
    print('predition= ')
    for i in range(num_work):
        print("\n-----Test %d-----\n" % i)
        print(predictions[i])
        print()

    if args.dump:
        with open(args.csv + '.txt', 'w') as ftxt, open(args.csv + '.out', 'w') as fout:
            for wav, txt, out in zip(wavlist, ground_truths, predictions):
                ftxt.write('%s %s\n' % (wav, txt))
                fout.write('%s %s\n' % (wav, out))
            print('Reference texts dumped to %s.txt' % args.csv)
            print('Transcription   dumped to %s.out' % args.csv)

if __name__ == '__main__':
    main()
