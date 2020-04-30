"""

Read and prepare data

"""

import scipy.io as sio
import numpy as np
from sklearn.model_selection import train_test_split
from dataset import ndarrayDataset


data_location = "/mnt/storage/tmwang/Materials/MP.mat"

data = sio.loadmat(data_location)

input_mat = data['MP']

# count data in different classes
id = input_mat[:,0]
atom_type = input_mat[:,1]
energy = input_mat[:,2] # target value
X = input_mat[:,3:] # training data

y = atom_type - 1

# for i in range(7):
#     cnt = np.count_nonzero(atom_type == (i+1))
#     print("Type %d : %d" % (i+1, cnt))
print(np.max(y),np.min(y))

# First train everything
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=9)

for i in range(7):
    cnt = np.count_nonzero(y_train == i)
    print("Type %d : %d" % (i+1, cnt))
for i in range(7):
    cnt = np.count_nonzero(y_test == i)
    print("Type %d : %d" % (i+1, cnt))
"""

Body part of train/test

"""

import argparse
import torch
import torch.utils.data
from torch import nn, optim
from torch.utils.data import DataLoader
from loss_function import simplevae_elbo_loss_function
from model.baselines import SimpleVAE

parser = argparse.ArgumentParser(description='Test')
parser.add_argument('--batch-size', type=int, default=128, metavar='N',
                    help='input batch size for training (default: 128)')
parser.add_argument('--epochs', type=int, default=100, metavar='N',
                    help='number of epochs to train (default: 10)')
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='enables CUDA training')
parser.add_argument('--seed', type=int, default=9, metavar='S',
                    help='random seed (default: 9)')
parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                    help='how many batches to wait before logging training status')
parser.add_argument('--gpu', type=int, default=0, metavar='G',
                    help='gpu card id (default: 0)')
args = parser.parse_args()
print(args)
args.cuda = not args.no_cuda and torch.cuda.is_available()

torch.manual_seed(args.seed)

device = torch.device("cuda:%d" % args.gpu if args.cuda else "cpu")

kwargs = {'num_workers': 1, 'pin_memory': True} if args.cuda else {}

train_dataset = ndarrayDataset(X_train,y_train)
train_loader = DataLoader(train_dataset, batch_size = args.batch_size, shuffle=True)
train_losses = np.zeros((args.epochs))
test_dataset = ndarrayDataset(X_test,y_test)
test_loader = DataLoader(test_dataset, batch_size=1)
test_losses = np.zeros((args.epochs))

model = SimpleVAE(3600,200,40).to(device)
optimizer = optim.Adam(model.parameters(), lr=1e-3)


def train(epoch):
    model.train()
    train_loss = 0
    correct = 0
    for batch_idx, (data, y) in enumerate(train_loader):
        data = data.to(device)
        y = y.long().to(device)
        optimizer.zero_grad()
        y_pred, mu, logvar = model(data)
        loss = simplevae_elbo_loss_function(y_pred, y, mu, logvar)
        loss.backward()
        train_loss += loss.item()
        optimizer.step()
        pred = y_pred.argmax(dim=1, keepdim=True)  # get the index of the max log-probability
        correct += pred.eq(y.view_as(pred)).sum().item()
        if batch_idx % args.log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader),
                loss.item() / len(data)))

    print('====> Epoch: {} Average loss: {:.4f}'.format(
          epoch, train_loss / len(train_loader.dataset)))
    return 100. * correct / len(train_loader.dataset)


def test(epoch):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for i, (data, y) in enumerate(test_loader):
            data = data.to(device)
            y = y.long().to(device)
            y_pred, mu, logvar = model(data)
            test_loss += (simplevae_elbo_loss_function(y_pred, y, mu, logvar).item())
            pred = y_pred.argmax(dim=1, keepdim=True)  # get the index of the max log-probability
            correct += pred.eq(y.view_as(pred)).sum().item()

    test_loss /= len(test_loader.dataset)
    print('====> Test set loss: {:.4f}'.format(test_loss))
    return 100. * correct / len(test_loader.dataset)



if __name__ == "__main__":
    train_acc_list = []
    test_acc_list = []
    for epoch in range(1, args.epochs + 1):
        train_acc = train(epoch)
        test_acc = test(epoch)
        train_acc_list.append(train_acc)
        test_acc_list.append(test_acc)
    with open('checkpoints/simpleVAE.npz','wb') as f:
        np.savez(f, train_acc = train_acc_list, test_acc = test_acc_list)
