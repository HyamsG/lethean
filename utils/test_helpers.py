import time
import numpy as np
import torch
import torch.nn as nn
from utils.misc import *

device = 'cuda' if torch.cuda.is_available() else 'cpu'

def test(teloader, model, verbose=False, print_freq=10):
    model.eval()
    batch_time = AverageMeter('Time', ':6.3f')
    top1 = AverageMeter('Acc@1', ':6.2f')
    progress = ProgressMeter(len(teloader), batch_time, top1, prefix='Test: ')

    one_hot = []
    losses = []
    criterion = nn.CrossEntropyLoss(reduction='none').to(device)
    end = time.time()
    correct_per_class = [0 for i in range(10)]
    total_per_class = [0 for i in range(10)]
    for i, (inputs, labels) in enumerate(teloader):
        with torch.no_grad():
            inputs, labels = inputs.to(device), labels.to(device)
            outputs, _ = model(inputs)
            _, predicted = outputs.max(1)
            losses.append(criterion(outputs, labels).cpu())
            one_hot.append(predicted.eq(labels).cpu())

        for j in range(len(labels)):
            lbl = labels[j]
            total_per_class[lbl] += 1
            correct_per_class[lbl] += int(one_hot[-1][j].item())
        acc1 = one_hot[-1].sum().item() / len(labels)
        top1.update(acc1, len(labels))
        batch_time.update(time.time() - end)
        end = time.time()

        if print_freq > 0 and i % print_freq == 0:
            progress.print(i)
    print(' * Acc@1 {top1.avg:.3f}'.format(top1=top1))

    if verbose:
        one_hot = torch.cat(one_hot).numpy()
        losses = torch.cat(losses).numpy()
        # return 1-top1.avg, one_hot, losses
        return 1-top1.avg, correct_per_class, total_per_class
    else:
        return 1-top1.avg

def pair_buckets(o1, o2):
    crr = np.logical_and( o1, o2 )
    crw = np.logical_and( o1, np.logical_not(o2) )
    cwr = np.logical_and( np.logical_not(o1), o2 )
    cww = np.logical_and( np.logical_not(o1), np.logical_not(o2) )
    return crr, crw, cwr, cww
def count_each(tuple):
    return [item.sum() for item in tuple]
