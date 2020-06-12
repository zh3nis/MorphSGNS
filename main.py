import argparse
import time
import torch
import gensim
from gensim.models import KeyedVectors
from gensim.test.utils import datapath
import os

import data
import model

import morfessor


os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"

parser = argparse.ArgumentParser(description='PyTorch SGNS and LogitSGNS Models',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--data', type=str, default='data/text8',
                    help='location of the data corpus')
parser.add_argument('--save_dir', type=str, default='embeddings',
                    help='path to save the word vectors')
parser.add_argument('--save_file', type=str, default='sgns',
                    help='path to save the word vectors')                    
parser.add_argument('--emsize', type=int, default=200,
                    help='size of word embeddings')
parser.add_argument('--epochs', type=int, default=30,
                    help='upper epoch limit')
parser.add_argument('--batch_size', type=int, default=1024,
                    help='batch size')
parser.add_argument('--window_size', type=int, default=5,
                    help='context window size')
parser.add_argument('--neg_num', type=int, default=5,
                    help='negative samples per training example')
parser.add_argument('--min_count', type=int, default=5,
                    help='number of word occurrences for it to be included in the vocabulary')
parser.add_argument('--gpu', default='0',
                    help='GPU to use')

args = parser.parse_args()


if not os.path.exists(args.save_dir):
  os.makedirs(args.save_dir)

my_data = data.DataReader(args.data, args.min_count)
dataset = data.Word2vecDataset(my_data, args.window_size, args.neg_num)
dataloader = torch.utils.data.DataLoader(
  dataset, batch_size=args.batch_size, collate_fn=dataset.collate)

vocab_size = len(my_data.word2id)
morph_sgns_model = model.MorphSGNS(vocab_size, args.emsize, word2morph)

os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
use_cuda = torch.cuda.is_available()
device = torch.device("cuda" if use_cuda else "cpu")
if use_cuda: skip_gram_model.cuda()

epoch_size = dataset.data_len // args.batch_size
optimizer = torch.optim.Adam(skip_gram_model.parameters())

for epoch in range(args.epochs):
  last_time = time.time()
  last_words = 0

  total_loss = 0.0
  
  for step, batch in enumerate(dataloader):
    pos_u = batch[0].to(device)
    pos_v = batch[1].to(device)
    neg_v = batch[2].to(device)

    optimizer.zero_grad()
    loss = skip_gram_model.forward(pos_u, pos_v, neg_v)
    loss.backward()
    optimizer.step()

    total_loss += loss.item()

    if step % (epoch_size // 10) == 10:
      print('%.2f' % (step * 1.0 / epoch_size), end=' ')
      print('loss = %.3f' % (total_loss / (step + 1)), end=', ')
      now_time = time.time()
      now_words = step * args.batch_size
      wps = (now_words - last_words) / (now_time - last_time)
      print('wps = ' + str(int(wps)))
      last_time = now_time
      last_words = now_words

  print("Epoch: " + str(epoch + 1), end=", ")
  print("Loss = %.3f" % (total_loss / epoch_size), end=", ")

  skip_gram_model.save_embedding(my_data.id2word, os.path.join(args.save_dir, args.save_file))
  wv_from_text = KeyedVectors.load_word2vec_format(os.path.join(args.save_dir, args.save_file), binary=False)
  ws353 = wv_from_text.evaluate_word_pairs(datapath('wordsim353.tsv'))
  google = wv_from_text.evaluate_word_analogies(datapath('questions-words.txt'))
  print('WS353 = %.3f' % ws353[0][0], end=', ')
  print('Google = %.3f' % google[0])