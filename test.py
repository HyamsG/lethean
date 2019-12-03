from __future__ import print_function
import argparse
import torch
import torch.nn as nn
import torch.optim as optim

from utils.misc import *
from utils.adapt_helpers import *
from utils.rotation import rotate_batch
from utils.model import resnet18
from utils.train_helpers import normalize
from utils.test_helpers import test

import matplotlib.pyplot as plt

def imshow(img):
    img = img / 2 + 0.5     # unnormalize
    npimg = img.numpy()
    plt.imshow(np.transpose(npimg, (1, 2, 0)))
    plt.show()

device = 'cuda' if torch.cuda.is_available() else 'cpu'

classes = ('plane', 'car', 'bird', 'cat',
           'deer', 'dog', 'frog', 'horse', 'ship', 'truck')

parser = argparse.ArgumentParser()
parser.add_argument('--level', default=0, type=int)
parser.add_argument('--corruption', default='original')
parser.add_argument('--corruption2', default='original')
parser.add_argument('--corruption3', default='original')
parser.add_argument('--dataroot', default='data/CIFAR-10-C/')
parser.add_argument('--shared', default=None)
########################################################################
parser.add_argument('--depth', default=18, type=int)
parser.add_argument('--group_norm', default=32, type=int)
parser.add_argument('--batch_size', default=32, type=int)
########################################################################
parser.add_argument('--lr', default=0.001, type=float)
parser.add_argument('--niter', default=10, type=int)
parser.add_argument('--online', action='store_true')
parser.add_argument('--shuffle', action='store_true')
parser.add_argument('--threshold', default=1, type=float)
parser.add_argument('--dset_size', default=0, type=int)
########################################################################
parser.add_argument('--resume', default=None)
parser.add_argument('--outf', default='.')

args = parser.parse_args()
args.threshold += 0.001		# to correct for numeric errors
my_makedir(args.outf)
import torch.backends.cudnn as cudnn
cudnn.benchmark = True

def gn_helper(planes):
    return nn.GroupNorm(args.group_norm, planes)
norm_layer = gn_helper

net = resnet18(num_classes = 10, norm_layer=norm_layer).to(device)
net = torch.nn.DataParallel(net)

print('Resuming from %s...' %(args.resume))
ckpt = torch.load('%s/best.pth' %(args.resume))
net.load_state_dict(ckpt['net'])

criterion = nn.CrossEntropyLoss().to(device)
optimizer = optim.SGD(net.parameters(), lr=args.lr)

print('Loading data... (Corruption: %s, Level: %d)' % (args.corruption, args.level))
np_labels = np.load(args.dataroot + "labels.npy")
np_all = np.load(args.dataroot + args.corruption + ".npy")
np_labels = np_labels[((args.level - 1) * 10000):(args.level*10000)]
np_all = np_all[((args.level - 1) * 10000):(args.level*10000), ]

print('Loading data... (Corruption: %s, Level: %d)' % (args.corruption2, args.level))
np_all2 = np.load(args.dataroot + args.corruption2 + ".npy")
np_all2 = np_all2[((args.level - 1) * 10000):(args.level*10000), ]

print('Loading data... (Corruption: %s, Level: %d)' % (args.corruption3, args.level))
np_all3 = np.load(args.dataroot + args.corruption3 + ".npy")
np_all3 = np_all3[((args.level - 1) * 10000):(args.level*10000), ]

_, teloader = prepare_test_data(args)

print('Running original network on the whole corrupted data...')
correct_orig = []
for i in range(0, len(np_all)):
    label = np_labels[i]
    img = np_all[i, ]

    correctness, _ = test_single(net, img, label)
    correct_orig.append(correctness)
    if i % 1000 == 999:
        print("%d%%" % ((i  + 1) * 100 / len(np_all)))
print('Test error cls %.2f' %((1-mean(correct_orig))*100))

print('Running original network on the whole corrupted (2) data...')
correct_orig2 = []
for i in range(0, len(np_all)):
    label = np_labels[i]
    img = np_all2[i, ]

    correctness, _ = test_single(net, img, label)
    correct_orig2.append(correctness)
    if i % 1000 == 999:
        print("%d%%" % ((i  + 1) * 100 / len(np_all2)))
print('Test error cls %.2f' %((1-mean(correct_orig2))*100))

print('Running original network on the whole corrupted (2) data...')
correct_orig3 = []
for i in range(0, len(np_all)):
    label = np_labels[i]
    img = np_all3[i, ]

    correctness, _ = test_single(net, img, label)
    correct_orig3.append(correctness)
    if i % 1000 == 999:
        print("%d%%" % ((i  + 1) * 100 / len(np_all2)))
print('Test error cls %.2f' %((1-mean(correct_orig3))*100))

err_cls = test(teloader, net)
print("Original test error: %.2f" % err_cls)

for j in range(10):
    if j % 3 == 0:
        crpt = args.corruption
        crpt_data = np_all
    elif j % 3 == 1:
        crpt = args.corruption2
        crpt_data = np_all2
    else:
        crpt = args.corruption3
        crpt_data = np_all3
    print('Running TTL network (online) #%d, with corruption %s...' % (j, crpt))
    correct_ttl = []
    confs = []
    for i in range(j * 1000, (j + 1) * 1000):
        label = np_labels[i]
        img = crpt_data[i, ]

        _, confidence = test_single(net, img, label)
        confs.append(confidence)
        if confidence < args.threshold:
            adapt_single(net, img, optimizer, criterion, args.niter, args.batch_size)
        correctness, _ = test_single(net, img, label)
        correct_ttl.append(correctness)
    print('Done, Test error cls %.2f' %((1-mean(correct_ttl))*100))

    err_cls = test(teloader, net)
    print("Original test error: %.2f" % err_cls)
